import os
import requests
import base64
import xmltodict
from django.shortcuts import render, redirect
from django.http import HttpResponse
from roboprop_client.utils import unflatten_dict

headers = {"X-DreamFactory-API-Key": os.getenv("FILESERVER_API_KEY")}
fileserver_url = os.getenv("FILESERVER_URL")


def _make_get_request(url):
    return requests.get(url, headers=headers)


def _get_models(url):
    models = []
    response = _make_get_request(url)
    data = response.json()["resource"]
    for item in data:
        if item["type"] == "folder":
            models.append(item["name"])
    return models


def _get_roboprop_model_thumbnails(models, gallery=True):
    thumbnails = []
    for model in models:
        url = fileserver_url + model + "/thumbnails/"
        response = _make_get_request(url)
        if response.status_code == 200:
            thumbnail_data = response.json()["resource"]
            if gallery:
                # Just one thumbnail for each in mymodels.html
                thumbnail_data = thumbnail_data[0:1]
            for data in thumbnail_data:
                url = fileserver_url + data["path"] + "?is_base64=true"
                response = _make_get_request(url)
                thumbnail = base64.b64encode(response.content).decode("utf-8")
                thumbnails.append({"name": model, "image": thumbnail})
        else:
            # Just show a placeholder.
            thumbnails.append({"name": model, "image": None})
    return thumbnails


def _get_model_configuration(model):
    url = fileserver_url + model + "/model.config"
    response = _make_get_request(url)
    xml_string = response.content.decode("utf-8")
    # Parse as dictionary
    xml_dict = xmltodict.parse(xml_string)

    model_configuration = xml_dict["model"] if "model" in xml_dict else xml_dict
    return model_configuration


def _config_as_xml(config, asset_type):
    # xmltodict seems happy with a lists of length>1 (so that it allows for multiple
    # tags with the same name), but seemingly not just length 1 which is what a django
    # form gives us (querydict). So we convert any lists of length 1 to a string.
    for key, value in config.items():
        if isinstance(value, list) and len(value) == 1:
            config[key] = str(value[0])

    config = {asset_type: unflatten_dict(config)}
    # Yes, weird but http request doesnt seem to like it unless
    # triple quoted. the final ">" seems to get cut off otherwise.
    xml_string = f"""{xmltodict.unparse(config, pretty=True)}
"""
    return xml_string


def home(request):
    return render(request, "home.html")


def mymodels(request):
    roboprop_models = _get_models(fileserver_url)
    roboprop_model_thumbnails = _get_roboprop_model_thumbnails(roboprop_models)
    fuel_thumbnails = []  # TODO:
    gallery_thumbnails = roboprop_model_thumbnails + fuel_thumbnails

    return render(request, "mymodels.html", {"thumbnails": gallery_thumbnails})


def mymodel_detail(request, model):
    # Using POST to save ourselves writing a bunch of JS
    # the final API call will be PUT.
    if request.method == "POST":
        # Convert a Django QueryDict to a dictionary
        model_config = dict(request.POST)
        model_config.pop("csrfmiddlewaretoken", None)
        print(model_config)
        # Convert to xml before making out PUT request to update.
        model_config = _config_as_xml(model_config, "model")
        # Send an HTTP PUT request to update the model configuration
        url = fileserver_url + model + "/model.config"
        response = requests.put(url, data=model_config, headers=headers)
        response.raise_for_status()
        return redirect("mymodel_detail", model=model)

    # GET
    model_details = {
        "name": model,
        "thumbnails": [],
        "configuration": {},
    }

    thumbnails = _get_roboprop_model_thumbnails([model], gallery=False)
    for thumbnail in thumbnails:
        model_details["thumbnails"].append(thumbnail["image"])
    model_details["configuration"] = _get_model_configuration(model)

    return render(request, "mymodel_detail.html", {"model": model_details})
