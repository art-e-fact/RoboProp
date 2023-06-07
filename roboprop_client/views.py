import os
import requests
import base64
from django.shortcuts import render
from django.http import HttpResponse

headers = {"X-DreamFactory-API-Key": os.getenv("FILESERVER_API_KEY")}
fileserver_url = os.getenv("FILESERVER_URL")


def _make_get_request(url):
    return requests.get(url, headers=headers)


def _get_models(asset_library):
    if asset_library == "roboprop":
        url = fileserver_url + "?full_tree=true&as_list=true"
        response = _make_get_request(url)
        data = response.json()["resource"]
    return data


def _get_roboprop_model_thumbnails(models):
    thumbnails = {}
    for model in models:
        if "thumbnails" in model and not model.endswith("/"):
            name = model.split("/")[0]
            url = fileserver_url + model + "?is_base64=true"
            response = _make_get_request(url)
            thumbnail_base64 = base64.b64encode(response.content).decode("utf-8")
            # Ensure only one thumbnail per model
            if name not in thumbnails:
                thumbnails[name] = thumbnail_base64
    return [
        {"name": name, "image": thumbnail_base64}
        for name, thumbnail_base64 in thumbnails.items()
    ]


def home(request):
    return render(request, "home.html")


def mymodels(request):
    roboprop_models = _get_models("roboprop")
    roboprop_model_thumbnails = _get_roboprop_model_thumbnails(roboprop_models)
    fuel_thumbnails = []  # TODO:
    thumbnails = roboprop_model_thumbnails + fuel_thumbnails

    return render(request, "mymodels.html", {"thumbnails": thumbnails})


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
