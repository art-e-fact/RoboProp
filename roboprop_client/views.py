import os
import requests
import base64
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
            thumbnails.append({"name": model, "image": None})
    return thumbnails


def home(request):
    return render(request, "home.html")


def mymodels(request):
    roboprop_models = _get_models(fileserver_url)
    roboprop_model_thumbnails = _get_roboprop_model_thumbnails(roboprop_models)
    fuel_thumbnails = []  # TODO:
    gallery_thumbnails = roboprop_model_thumbnails + fuel_thumbnails

    return render(request, "mymodels.html", {"thumbnails": gallery_thumbnails})


def mymodel_detail(request, model):
    # url = f"https://example.com/api/{model}/"  # Replace with your API endpoint URL
    # response = requests.get(url)
    # if response.status_code == 200:
    #     data = response.json()
    #     return render(request, "mymodel_detail.html", {"data": data})
    # else:
    #     return HttpResponse("Error: Could not retrieve data")
    model = {
        "name": model,
        "description": "This is a description of the model",
    }
    return render(request, "mymodel_detail.html", {"model": model})
