import os
import requests
import base64
import xmltodict
from django.shortcuts import render
from django.http import HttpResponse

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


def home(request):
    return render(request, "home.html")


def mymodels(request):
    roboprop_models = _get_models(fileserver_url)
    roboprop_model_thumbnails = _get_roboprop_model_thumbnails(roboprop_models)
    fuel_thumbnails = []  # TODO:
    gallery_thumbnails = roboprop_model_thumbnails + fuel_thumbnails

    return render(request, "mymodels.html", {"thumbnails": gallery_thumbnails})


def mymodel_detail(request, model):
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
