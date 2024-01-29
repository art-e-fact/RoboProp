import requests
import boto3
import base64
import xmltodict
import json
import os
import urllib.parse
import subprocess
import zipfile
import shutil
import math
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.core.cache import cache
from django.contrib import auth
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from roboprop_client.load_blenderkit import load_blenderkit_model
import roboprop_client.utils as utils


# We use a custom decorator as user login is through DreamFactory, not Django
def login_required(view_func):
    def _wrapped_view_func(request, *args, **kwargs):
        if "session_token" not in request.session:
            messages.error(request, "You need to be logged in to access this page.")
            return redirect("login")
        return view_func(request, *args, **kwargs)

    return _wrapped_view_func


def _get_assets(url):
    assets = []
    response = utils.make_get_request(url)
    # If the folder doesn't exist, return an empty list
    if response.status_code == 404:
        return assets
    data = response.json()["resource"]
    for item in data:
        if item["type"] == "folder":
            assets.append(item["name"])
    return assets


def _get_thumbnails(assets, asset_type, page=1, page_size=12, gallery=True):
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    assets = assets[start_index:end_index]
    thumbnails = []
    for asset in assets:
        url = f"files/{asset_type}/{asset}/thumbnails/"
        response = utils.make_get_request(url)
        if response.status_code == 200:
            thumbnail_data = response.json()["resource"]
            if gallery:
                # Just one thumbnail for each in mymodels.html
                thumbnail_data = thumbnail_data[0:1]
            for data in thumbnail_data:
                url = f"files/{data['path']}?is_base64=true"
                response = utils.make_get_request(url)
                thumbnail = base64.b64encode(response.content).decode("utf-8")
                thumbnails.append({"name": asset, "image": thumbnail})
        else:
            # Just show a placeholder.
            thumbnails.append({"name": asset, "image": None})
    return thumbnails


def _get_all_thumbnails(asset_type, page=1, page_size=12):
    assets = _get_assets(f"files/{asset_type}/")
    if not assets:
        return []
    thumbnails = _get_thumbnails(assets, asset_type, page, page_size)
    return thumbnails


def _get_model_configuration(model):
    url = f"files/models/{model}/model.config"
    response = utils.make_get_request(url)
    response.raise_for_status()
    xml_string = response.content.decode("utf-8")
    try:
        xml_dict = xmltodict.parse(xml_string)
        model_configuration = xml_dict["model"] if "model" in xml_dict else xml_dict
        # Convert to a flat dictionary using dot notation
        model_configuration = utils.flatten_dict(model_configuration)
    except (TypeError, KeyError) as e:
        raise ValueError(f"Failed to parse model configuration for {model}: {e}")
    return model_configuration


def _search_external_library(query, library):
    response = requests.get(query)
    search_results = (
        response.json()["results"] if library == "blenderkit" else response.json()
    )
    return search_results


def _search_and_cache(search):
    # Check if the results are already cached
    cache_key = f"search_results_{search}"
    search_results = cache.get(cache_key)
    blenderkit_free = False if len(utils.BLENDERKIT_PRO_API_KEY) > 0 else True

    # i.e if there is no cache
    if not search_results:
        search_results = {
            "fuel": _search_external_library(
                f"https://fuel.gazebosim.org/1.0/models?q={search}", "fuel"
            ),
            "blenderkit": _search_external_library(
                f"https://www.blenderkit.com/api/v1/search/?query=search+text:{search}+asset_type:model+order:_score+is_free:{blenderkit_free}&page=1",
                "blenderkit",
            ),
        }
        # Cache the results for 5 minutes
        cache.set(cache_key, search_results, 300)

    return search_results


def _remove_outliers_and_sort(items):
    # Remove single occurences as is most likely an outlier
    items = [item for item in items if items.count(item) > 1]
    # Sort by most occurences
    sorted(items, key=lambda x: items.count(x), reverse=True)
    # Remove duplicates
    items = list(set(items))
    return items


def _detect_thumbnail_details(thumbnail):
    client = boto3.client("rekognition")

    # Confidence can be tweaked, and a lower value does return
    # more (and sometimes correct) results, but also more noise.
    response = client.detect_labels(
        Image={"Bytes": base64.b64decode(thumbnail)},
        Features=["GENERAL_LABELS", "IMAGE_PROPERTIES"],
        MinConfidence=90,
    )

    tags = []
    categories = []
    colors = []

    for label in response["Labels"]:
        tags.append(label["Name"])
        categories.append(label["Categories"][0]["Name"])
        if len(label["Parents"]) > 0:
            # Duplicates handled by _remove_outliers_and_sort()
            categories.append(label["Parents"][0]["Name"])

        if len(label["Instances"]) > 0:
            for dominant_color in label["Instances"][0]["DominantColors"]:
                colors.append(dominant_color["SimplifiedColor"])

    return tags, categories, colors


def _get_suggested_tags(thumbnails):
    tags = []
    categories = []
    colors = []

    for thumbnail in thumbnails:
        t, c, col = _detect_thumbnail_details(thumbnail)
        tags.extend(t)
        categories.extend(c)
        colors.extend(col)

    tags = _remove_outliers_and_sort(tags)
    categories = _remove_outliers_and_sort(categories)
    colors = _remove_outliers_and_sort(colors)

    return tags, categories, colors


def _get_blenderkit_metadata(folder_name):
    tags = []
    categories = []
    description = []
    url = f"files/models/{folder_name}/blenderkit_meta.json"
    response = utils.make_get_request(url)
    if response.status_code == 200:
        metadata = response.json()
        tags = metadata.get("tags", [])
        # Blenderkit has only one category per model, but this
        # is a list for consistency
        categories = [metadata.get("category", "").strip()]
        description = metadata.get("description", "")
    return tags, categories, description


def _get_blenderkit_model_details(result):
    return {
        "name": result["name"],
        "thumbnail": result["thumbnailMiddleUrl"],
        "description": result["description"],
        "assetBaseId": result["assetBaseId"],
    }


def _get_fuel_model_details(result):
    thumbnail_url = result.get("thumbnail_url", None)
    return {
        "name": result["name"],
        "owner": result["owner"],
        "description": result["description"],
        "thumbnail": thumbnail_url,
    }


def _add_fuel_model_to_my_models(name, owner):
    # make a POST Request to our fileserver
    url = f"files/models/{name}/"
    parameters = f"?url=https://fuel.gazebosim.org/1.0/{owner}/models/{name}.zip&extract=true&clean=true"
    response = utils.make_post_request(url, parameters=parameters)
    return response


def _add_blenderkit_thumbnail(thumbnail, folder_name):
    thumbnail_response = requests.get(thumbnail)
    os.makedirs(os.path.join("models", folder_name, "thumbnails"), exist_ok=True)
    thumbnail_filename = os.path.basename(thumbnail)
    thumbnail_extension = os.path.splitext(thumbnail_filename)[1]
    new_thumbnail_filename = "01" + thumbnail_extension
    thumbnail_path = os.path.join(
        "models", folder_name, "thumbnails", new_thumbnail_filename
    )
    with open(thumbnail_path, "wb") as thumbnail_file:
        thumbnail_file.write(thumbnail_response.content)


def _add_blenderkit_model_to_my_models(folder_name, asset_base_id, thumbnail):
    load_blenderkit_model(asset_base_id, "models", folder_name)

    _add_blenderkit_thumbnail(thumbnail, folder_name)
    zip_filename, zip_path = utils.create_zip_file(folder_name)
    # Upload the ZIP file in a POST request
    with open(zip_path, "rb") as zip_file:
        files = {"files": (zip_filename, zip_file)}
        asset_name = os.path.splitext(zip_filename)[0]
        url = f"files/models/{asset_name}/"
        response = utils.make_post_request(url, files=files)

    utils.delete_folders(["models", "textures"])
    return response


def _create_metadata_from_rekognition(name):
    thumbnails = _get_thumbnails([name], "models", page=1, page_size=1, gallery=False)
    tags, categories, colors = [], [], []
    if all(thumbnail["image"] is not None for thumbnail in thumbnails):
        base64_thumbnails = list(thumbnail["image"] for thumbnail in thumbnails)
        tags, categories, colors = _get_suggested_tags(base64_thumbnails)
    return tags, categories, colors


def _check_and_get_index(request):
    response = utils.make_get_request("files/index.json")
    if response.status_code == 200:
        # Convert the JSON response to a dictionary
        index = json.loads(response.content)
    elif response.status_code == 404:
        index = {}
    else:
        messages.error(request, "Failed to fetch index.json")
        return redirect("mymodels")
    return index


def _update_index(request, model_name, model_metadata, model_source):
    index = _check_and_get_index(request)
    url_safe_name = urllib.parse.quote(model_name)
    model_metadata["source"] = model_source
    model_metadata["scale"] = 1.0
    model_metadata["url"] = (
        utils.FILESERVER_URL + f"files/models/{url_safe_name}/?zip=true"
    )
    index[model_name] = model_metadata
    response = utils.make_put_request("files/index.json", data=json.dumps(index))
    return response


def _add_blenderkit_model_metadata(request, folder_name, asset_base_id):
    tags, categories, description = _get_blenderkit_metadata(folder_name)
    metadata = {
        "tags": tags,
        "categories": categories,
        "description": description,
        "assetBaseId": asset_base_id,
    }
    source = "Blenderkit_pro" if len(utils.BLENDERKIT_PRO_API_KEY) > 0 else "Blenderkit"
    response = _update_index(request, folder_name, metadata, source)
    return response


def _add_fuel_model_metadata(request, name, description):
    tags, categories, colors = _create_metadata_from_rekognition(name)
    metadata = {
        "tags": tags,
        "categories": categories,
        "colors": colors,
        "description": description,
    }

    response = _update_index(request, name, metadata, "Fuel")
    return response


def _get_num_assets(asset_type):
    assets = _get_assets(f"files/{asset_type}/")
    if not assets:
        return 0
    return len(assets)


def _login_to_fileserver(username, password):
    user_url = "user/session"
    admin_url = "system/admin/session"
    login_credentials = {"email": username, "password": password, "remember_me": False}
    user_response = utils.make_post_request(user_url, json=login_credentials)
    if user_response.status_code == 200:
        session_token = user_response.json()["session_token"]
        return session_token, True
    elif user_response.status_code == 401:
        admin_response = utils.make_post_request(admin_url, json=login_credentials)
        if admin_response.status_code == 200:
            session_token = admin_response.json()["session_token"]
            return session_token, True
    else:
        return None


"""VIEWS"""

def home(request):
    if request.user.id is None:
        return redirect("login")
    return render(request, "home.html")


def login(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        result = _login_to_fileserver(username, password)
        if result is not None:
            session_token, success = result
            if success:
                user, created = User.objects.get_or_create(username=username)
                if created:
                    # Prevents login via Django's authentication system
                    user.set_unusable_password()
                    user.save()
                auth.login(request, user)
                request.session["session_token"] = session_token
                return redirect("home")
        else:
            messages.error(request, "Invalid credentials")
            return render(request, "login.html")
    return render(request, "login.html")


@login_required
def logout(request):
    auth.logout(request)
    if "session_token" in request.session:
        del request.session["session_token"]
    return redirect("login")


@login_required
def mymodels(request):
    page = int(request.GET.get("page", 1))
    page_size = int(request.GET.get("page_size", 12))
    if request.method == "POST":
        file = request.FILES["file"]
        response = utils.upload_file(file, "models")
        if response.status_code == 201:
            messages.success(request, "Model uploaded successfully")
            model_name = os.path.splitext(file.name)[0]
            tags, categories, colors = _create_metadata_from_rekognition(model_name)
            request.session["model_meta_data"] = {
                "name": model_name,
                "tags": tags,
                "categories": categories,
                "colors": colors,
            }
            return redirect("add_metadata", name=model_name)
        else:
            messages.error(request, "Failed to upload model")
            return redirect("mymodels")

    total_num_models = _get_num_assets("models")
    total_pages = math.ceil(total_num_models / page_size)
    gallery_thumbnails = _get_all_thumbnails("models", page, page_size)
    return render(
        request,
        "mymodels.html",
        {
            "thumbnails": gallery_thumbnails,
            "page": page,
            "page_size": page_size,
            "total_models": total_num_models,
            "total_pages": total_pages,
        },
    )


@login_required
def mymodel_detail(request, name):
    model_details = {
        "name": name,
        "thumbnails": [],
        "configuration": {},
    }

    thumbnails = _get_thumbnails([name], "models", page=1, page_size=1, gallery=False)

    for thumbnail in thumbnails:
        model_details["thumbnails"].append(thumbnail["image"])
    model_details["configuration"] = _get_model_configuration(name)

    return render(request, "mymodel_detail.html", {"asset": model_details})


@login_required
def find_models(request):
    # Check if there is a search query via GET
    search = request.GET.get("search", "")
    blenderkit_id = request.GET.get("add-directly", "")
    fuel_models = []
    blenderkit_models = []

    if search:
        search_results = _search_and_cache(search)

        for result in search_results["fuel"]:
            fuel_model_details = _get_fuel_model_details(result)
            fuel_models.append(fuel_model_details)

        for result in search_results["blenderkit"]:
            blenderkit_model_details = _get_blenderkit_model_details(result)
            blenderkit_models.append(blenderkit_model_details)
    elif blenderkit_id:
        result = requests.get(
            f"https://www.blenderkit.com/api/v1/search/?query=asset_base_id:{blenderkit_id}"
        )
        data = result.json()["results"][0]
        blenderkit_model_details = _get_blenderkit_model_details(data)
        blenderkit_models.append(blenderkit_model_details)

    context = {
        "search": search,
        "fuel_models": fuel_models,
        "blenderkit_models": blenderkit_models,
    }
    return render(request, "find-models.html", context=context)


@login_required
def add_to_my_models(request):
    if request.method == "POST":
        name = request.POST.get("name")
        library = request.POST.get("library")
        if library == "fuel":
            owner = request.POST.get("owner")
            description = request.POST.get("description")
            response = _add_fuel_model_to_my_models(name, owner)
        elif library == "blenderkit":
            thumbnail = request.POST.get("thumbnail")
            asset_base_id = request.POST.get("assetBaseId")
            folder_name = utils.capitalize_and_remove_spaces(name)
            try:
                response = _add_blenderkit_model_to_my_models(
                    folder_name, asset_base_id, thumbnail
                )
            except ValueError as e:
                return JsonResponse({"error": str(e)}, status=500)
        metadata_response = None
        # If model upload succeeds, add metadata
        if response.status_code == 201 and library == "blenderkit":
            metadata_response = _add_blenderkit_model_metadata(
                request, folder_name, asset_base_id
            )
        elif response.status_code == 201 and library == "fuel":
            metadata_response = _add_fuel_model_metadata(request, name, description)
        else:
            response_data = {"error": f"Failed to add model: {name} to My Models"}
        # If both the model and metadata are successfully uploaded
        if metadata_response is not None:
            if metadata_response.status_code == 201:
                response_data = {
                    "message": f"Success: Model: {name} added to My Models, and successfully tagged"
                }
            else:
                response_data = {"error": f"Model: {name} uploaded, but failed to tag"}
        return JsonResponse(response_data, status=response.status_code)
    else:
        return JsonResponse({"error": "Invalid request method"}, status=405)


@login_required
def myrobots(request):
    if request.method == "POST":
        response = utils.upload_file(request.FILES["file"], "robots")
        if response.status_code == 201:
            messages.success(request, "Robot uploaded successfully")
        else:
            messages.error(request, "Failed to upload Robot")
        return redirect("myrobots")
    gallery_thumbnails = _get_all_thumbnails("robots")
    return render(request, "myrobots.html", {"thumbnails": gallery_thumbnails})


@login_required
def myrobot_detail(request, name):
    robot_details = {
        "name": name,
        "thumbnails": [],
    }

    thumbnails = _get_thumbnails([name], "robots", page=1, page_size=1, gallery=False)

    for thumbnail in thumbnails:
        robot_details["thumbnails"].append(thumbnail["image"])

    return render(request, "myrobot_detail.html", {"asset": robot_details})


@login_required
def add_metadata(request, name):
    if request.method == "POST":
        # Tags etc. that the user has selected based on
        # Rekognition suggestions
        tags = request.POST.getlist("tags")
        categories = request.POST.getlist("categories")
        colors = request.POST.getlist("colors")

        custom_field_index = {
            "custom-tags": tags,
            "custom-categories": categories,
            "custom-colors": colors,
        }
        # Tags etc. that the user has entered manually
        for custom_field, lst in custom_field_index.items():
            if request.POST.get(custom_field):
                lst.extend(
                    utils.create_list_from_string(request.POST.get(custom_field))
                )

        metadata = {
            "tags": tags,
            "categories": categories,
            "colors": colors,
        }

        response = _update_index(request, name, metadata, "Upload")
        if response.status_code == 201:
            messages.success(request, "Model tagged successfully")
        else:
            messages.error(request, "Failed to update index.json")

        return redirect("mymodels")

    # Metadata form shown after model upload. This page should
    # not be accessible unless the user has just uploaded a model.
    model_meta_data = request.session.get("model_meta_data")
    if model_meta_data:
        meta_data = {
            "tags": model_meta_data.get("tags"),
            "categories": model_meta_data.get("categories"),
            "colors": model_meta_data.get("colors"),
        }
        del request.session["model_meta_data"]
        return render(
            request, "add_metadata.html", {"name": name, "meta_data": meta_data}
        )
    else:
        messages.error(request, "No metadata available")
        return redirect("mymodels")


@login_required
def update_models_from_blenderkit(request):
    if request.method == "POST":
        # get index.json
        index = _check_and_get_index(request)
        for model in index:
            # check if model has key assetBaseId, i.e is from blenderkit
            if "assetBaseId" in index[model]:
                asset_base_id = index[model]["assetBaseId"]
                folder_name = model
                # Get the thumbnail from blenderkit, in case saved ones are lost
                result = requests.get(
                    f"https://www.blenderkit.com/api/v1/search/?query=asset_base_id:{asset_base_id}"
                )
                data = result.json()["results"][0]
                thumbnail = data["thumbnailMiddleUrl"]
                response = _add_blenderkit_model_to_my_models(
                    folder_name, asset_base_id, thumbnail
                )
                if response.status_code != 201:
                    return JsonResponse(
                        {"error": f"Update Failed"}, status=response.status_code
                    )
        # reupload index.json
        response = utils.make_put_request("files/index.json", data=json.dumps(index))
        if response.status_code == 201:
            return JsonResponse(
                {"message": f"Success: All models from blenderkit updated"}, status=201
            )
        else:
            return JsonResponse(
                {"error": f"Models updated, but index.json failed to reupload"},
                status=500,
            )
    else:
        return JsonResponse({"error": "Invalid request method"}, status=405)
