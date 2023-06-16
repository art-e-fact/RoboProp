import os
import requests
import base64
import xmltodict
import json
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from roboprop_client.utils import unflatten_dict, flatten_dict

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


def _get_roboprop_model_thumbnails(models, folder, gallery=True):
    thumbnails = []
    for model in models:
        url = fileserver_url + folder + "/" + model + "/thumbnails/"
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
                thumbnails.append(
                    {"name": model, "image": thumbnail, "folder": folder.rstrip("/")}
                )
        else:
            # Just show a placeholder.
            thumbnails.append(
                {"name": model, "image": None, "folder": folder.rstrip("/")}
            )
    return thumbnails


def _get_model_configuration(model, folder):
    url = fileserver_url + folder + "/" + model + "/model.config"
    response = _make_get_request(url)
    xml_string = response.content.decode("utf-8")
    # Parse as dictionary
    xml_dict = xmltodict.parse(xml_string)

    model_configuration = xml_dict["model"] if "model" in xml_dict else xml_dict
    # Convert to a flat dictionary
    model_configuration = flatten_dict(model_configuration)
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
    roboprop_models = _get_models(fileserver_url + "mymodels/")
    roboprop_model_thumbnails = _get_roboprop_model_thumbnails(
        roboprop_models, "mymodels"
    )
    fuel_thumbnails = _get_models(fileserver_url + "fuelmodels/")
    fuel_model_thumbnails = _get_roboprop_model_thumbnails(
        fuel_thumbnails, "fuelmodels"
    )
    gallery_thumbnails = roboprop_model_thumbnails + fuel_model_thumbnails

    return render(request, "mymodels.html", {"thumbnails": gallery_thumbnails})


def mymodel_detail(request, folder, name):
    # Using POST to save ourselves writing a bunch of JS
    # the final API call will be PUT.
    if request.method == "POST":
        # Convert a Django QueryDict to a dictionary
        model_config = dict(request.POST)
        model_config.pop("csrfmiddlewaretoken", None)
        # Convert to xml before making out PUT request to update.
        model_config = _config_as_xml(model_config, "model")
        # Send an HTTP PUT request to update the model configuration
        url = fileserver_url + "mymodels/" + name + "/model.config"
        response = requests.put(url, data=model_config, headers=headers)
        response.raise_for_status()
        return redirect("mymodel_detail", folder=folder, name=name)

    # GET
    model_details = {
        "name": name,
        "thumbnails": [],
        "configuration": {},
        "folder": folder.rstrip("/"),
    }

    thumbnails = _get_roboprop_model_thumbnails([name], folder, gallery=False)

    for thumbnail in thumbnails:
        model_details["thumbnails"].append(thumbnail["image"])
    model_details["configuration"] = _get_model_configuration(name, folder)

    return render(request, "mymodel_detail.html", {"model": model_details})


def find_models(request):
    # Check if there is a search query via GET
    search = request.GET.get("search", "")
    models = []

    if search:
        url = f"https://fuel.gazebosim.org/1.0/models?q={search}"
        response = requests.get(url)
        # Convert the response to a dictionary
        fuel_results = response.json()
        if fuel_results:
            for fuel_result in fuel_results:
                thumbnail_url = fuel_result.get("thumbnail_url", None)
                fuel_model = {
                    "type": "fuel",
                    "name": fuel_result["name"],
                    "owner": fuel_result["owner"],
                    "description": fuel_result["description"],
                    "thumbnail": thumbnail_url,
                }
                models.append(fuel_model)
    context = {
        "search": search,
        "models": models,
    }

    return render(request, "find-models.html", context=context)


def add_to_my_models(request):
    if request.method == "POST":
        name = request.POST.get("name")
        owner = request.POST.get("owner")
        # make a POST Request to our fileserver
        url = f"{fileserver_url}/fuelmodels/{name}/?url=https://fuel.gazebosim.org/1.0/{owner}/models/{name}.zip&extract=true&clean=true"
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        response_data = {"message": f"Success: Model: {name} added to My Models"}
        return JsonResponse(response_data)
    else:
        return JsonResponse({"error": "Invalid request method"})


# http://localhost/api/v2/files/fuel/3d_dollhouse_sofa/?url=https://fuel.gazebosim.org/1.0/GoogleResearch/models/3d_dollhouse_sofa.zip&extract=true&clean=true
