import os
import requests
import base64
import xmltodict
import json
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.core.cache import cache
from roboprop_client.utils import unflatten_dict, flatten_dict

FILESERVER_API_KEY = "X-DreamFactory-API-Key"
FILESERVER_API_KEY_VALUE = os.getenv("FILESERVER_API_KEY", "")
FILESERVER_URL = os.getenv("FILESERVER_URL", "")


def _make_get_request(url):
    return requests.get(url, headers={FILESERVER_API_KEY: FILESERVER_API_KEY_VALUE})


def _make_put_request(url, data):
    response = requests.put(
        url,
        data=data,
        headers={FILESERVER_API_KEY: FILESERVER_API_KEY_VALUE},
    )
    response.raise_for_status()


def _get_models(url):
    models = []
    response = _make_get_request(url)
    data = response.json()["resource"]
    for item in data:
        if item["type"] == "folder":
            models.append(item["name"])
    return models


def _get_model_thumbnails(models, folder, gallery=True):
    thumbnails = []
    for model in models:
        url = f"{FILESERVER_URL}{folder}/{model}/thumbnails/"
        response = _make_get_request(url)
        if response.status_code == 200:
            thumbnail_data = response.json()["resource"]
            if gallery:
                # Just one thumbnail for each in mymodels.html
                thumbnail_data = thumbnail_data[0:1]
            for data in thumbnail_data:
                url = f"{FILESERVER_URL}{data['path']}?is_base64=true"
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


def _get_all_model_thumbnails():
    roboprop_models = _get_models(FILESERVER_URL + "mymodels/")
    fuel_models = _get_models(FILESERVER_URL + "fuelmodels/")
    roboprop_model_thumbnails = _get_model_thumbnails(roboprop_models, "mymodels")
    fuel_model_thumbnails = _get_model_thumbnails(fuel_models, "fuelmodels")
    thumbnails = roboprop_model_thumbnails + fuel_model_thumbnails
    return thumbnails


def _get_model_configuration(model, folder):
    url = f"{FILESERVER_URL}{folder}/{model}/model.config"
    response = _make_get_request(url)
    response.raise_for_status()
    xml_string = response.content.decode("utf-8")
    try:
        xml_dict = xmltodict.parse(xml_string)
        model_configuration = xml_dict["model"] if "model" in xml_dict else xml_dict
        # Convert to a flat dictionary using dot notation
        model_configuration = flatten_dict(model_configuration)
    except (TypeError, KeyError) as e:
        raise ValueError(f"Failed to parse model configuration for {model}: {e}")
    return model_configuration


def _config_as_xml(config, asset_type):
    try:
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
    except (TypeError, KeyError) as e:
        raise ValueError(f"Failed to convert configuration to XML: {e}")


def _search_and_cache(search):
    # Check if the results are already cached
    cache_key = f"search_results_{search}"
    search_results = cache.get(cache_key)

    # i.e if there is no cache
    if not search_results:
        url = f"https://fuel.gazebosim.org/1.0/models?q={search}"
        response = requests.get(url)
        # Convert the response to a dictionary
        search_results = response.json()
        # Cache the results for 5 minutes
        cache.set(cache_key, search_results, 300)

    return search_results


def _get_model_details(result):
    thumbnail_url = result.get("thumbnail_url", None)
    return {
        "type": "fuel",
        "name": result["name"],
        "owner": result["owner"],
        "description": result["description"],
        "thumbnail": thumbnail_url,
    }


"""VIEWS"""


def home(request):
    return render(request, "home.html")


def mymodels(request):
    gallery_thumbnails = _get_all_model_thumbnails()
    return render(request, "mymodels.html", {"thumbnails": gallery_thumbnails})


def mymodel_detail(request, folder, name):
    # Using POST to save ourselves writing a bunch of JS
    # the final API call will be PUT.
    if request.method == "POST":
        # Convert a Django QueryDict to a dictionary
        model_config = dict(request.POST).pop("csrfmiddlewaretoken", None)
        # Convert to xml before making our PUT request to update.
        model_config = _config_as_xml(model_config, "model")
        # Send an HTTP PUT request to update the model configuration
        url = f"{FILESERVER_URL}{folder}/{name}/model.config"
        _make_put_request(url, model_config)
        return redirect("mymodel_detail", folder=folder, name=name)

    # GET
    model_details = {
        "name": name,
        "thumbnails": [],
        "configuration": {},
        "folder": folder.rstrip("/"),
    }

    thumbnails = _get_model_thumbnails([name], folder, gallery=False)

    for thumbnail in thumbnails:
        model_details["thumbnails"].append(thumbnail["image"])
    model_details["configuration"] = _get_model_configuration(name, folder)

    return render(request, "mymodel_detail.html", {"model": model_details})


def find_models(request):
    # Check if there is a search query via GET
    search = request.GET.get("search", "")
    models = []

    if search:
        search_results = _search_and_cache(search)

        for result in search_results:
            model_details = _get_model_details(result)
            models.append(model_details)

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
        url = f"{FILESERVER_URL}/fuelmodels/{name}/?url=https://fuel.gazebosim.org/1.0/{owner}/models/{name}.zip&extract=true&clean=true"
        response = requests.post(
            url, headers={FILESERVER_API_KEY: FILESERVER_API_KEY_VALUE}
        )
        response.raise_for_status()
        response_data = {"message": f"Success: Model: {name} added to My Models"}
        return JsonResponse(response_data)
    else:
        return JsonResponse({"error": "Invalid request method"})
