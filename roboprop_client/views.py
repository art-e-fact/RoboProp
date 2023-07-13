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
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.core.cache import cache
from django.contrib import auth
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
import roboprop_client.utils as utils


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


def _get_thumbnails(assets, asset_type, gallery=True):
    thumbnails = []
    for asset in assets:
        url = f"{asset_type}/{asset}/thumbnails/"
        response = utils.make_get_request(url)
        if response.status_code == 200:
            thumbnail_data = response.json()["resource"]
            if gallery:
                # Just one thumbnail for each in mymodels.html
                thumbnail_data = thumbnail_data[0:1]
            for data in thumbnail_data:
                url = f"{data['path']}?is_base64=true"
                response = utils.make_get_request(url)
                thumbnail = base64.b64encode(response.content).decode("utf-8")
                thumbnails.append({"name": asset, "image": thumbnail})
        else:
            # Just show a placeholder.
            thumbnails.append({"name": asset, "image": None})
    return thumbnails


def _get_all_thumbnails(asset_type):
    assets = _get_assets(f"{asset_type}/")
    if not assets:
        return []
    thumbnails = _get_thumbnails(assets, asset_type)
    return thumbnails


def _get_model_configuration(model):
    url = f"models/{model}/model.config"
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


def __search_external_library(query, library):
    response = requests.get(query)
    search_results = (
        response.json()["results"] if library == "blendkit" else response.json()
    )
    return search_results


def _search_and_cache(search):
    # Check if the results are already cached
    cache_key = f"search_results_{search}"
    search_results = cache.get(cache_key)

    # i.e if there is no cache
    if not search_results:
        search_results = {
            "fuel": __search_external_library(
                f"https://fuel.gazebosim.org/1.0/models?q={search}", "fuel"
            ),
            "blendkit": __search_external_library(
                f"https://www.blenderkit.com/api/v1/search/?query=search+text:{search}+asset_type:model+order:_score+is_free:True&page=1",
                "blendkit",
            ),
        }
        # Cache the results for 5 minutes
        cache.set(cache_key, search_results, 300)

    return search_results


def __remove_outliers_and_sort(items):
    # Remove single occurences as is most likely an outlier
    items = [item for item in items if items.count(item) > 1]
    # Sort by most occurences
    sorted(items, key=lambda x: items.count(x), reverse=True)
    # Remove duplicates
    items = list(set(items))
    return items


def __detect_thumbnail_details(thumbnail):
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
            # Duplicates handled by __remove_outliers_and_sort()
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
        t, c, col = __detect_thumbnail_details(thumbnail)
        tags.extend(t)
        categories.extend(c)
        colors.extend(col)

    tags = __remove_outliers_and_sort(tags)
    categories = __remove_outliers_and_sort(categories)
    colors = __remove_outliers_and_sort(colors)

    return tags, categories, colors


def _get_blendkit_model_details(result):
    return {
        "name": result["name"],
        "thumbnail": result["thumbnailMiddleUrl"],
        "assetBaseId": result["assetBaseId"],
    }


def _get_fuel_model_details(result):
    thumbnail_url = result.get("thumbnail_url", None)
    return {
        "name": result["name"],
        "owner": result["owner"],
        "thumbnail": thumbnail_url,
    }


def __add_fuel_model_to_my_models(name, owner):
    # make a POST Request to our fileserver
    url = f"models/{name}/"
    parameters = f"?url=https://fuel.gazebosim.org/1.0/{owner}/models/{name}.zip&extract=true&clean=true"
    response = utils.make_post_request(url, parameters=parameters)
    return response


# TODO: Convert blendkit model to SDF
def __add_blendkit_model_to_my_models(name, asset_base_id, thumbnail):
    url = f"models/"
    folder_name = utils.capitalize_and_remove_spaces(name)
    command = [
        "blenderproc",
        "run",
        "roboprop_client/load_blenderproc.py",
        "--asset_base_id",
        asset_base_id,
        "--output_path",
        "models",
        "--model_name",
        folder_name,
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    if process.returncode != 0:
        # Handle error
        print(f"Error running command: {command}")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        return response.status_code == 500
    else:
        # Handle success
        print(f"Command ran successfully: {command}")
        print(f"stdout: {stdout}")
        print(f"stderr: {stderr}")
        zip_filename = f"{folder_name}.zip"
        zip_path = os.path.join("models", zip_filename)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for root, dirs, files in os.walk(os.path.join("models", folder_name)):
                for file in files:
                    file_path = os.path.join(root, file)
                    zip_file.write(
                        file_path,
                        os.path.relpath(file_path, os.path.join("models", folder_name)),
                    )
        # Upload the ZIP file in a POST request
        with open(zip_path, "rb") as zip_file:
            files = {"files": (zip_filename, zip_file)}
            asset_name = os.path.splitext(zip_filename)[0]
            url = f"models/{asset_name}/"
            response = utils.make_post_request(url, files=files)

        if os.path.exists("models"):
            shutil.rmtree("models")
        if os.path.exists("textures"):
            shutil.rmtree("textures")
        return response


"""VIEWS"""


def home(request):
    if request.user.id is None:
        return redirect("login")

    return render(request, "home.html")


def login(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = auth.authenticate(request, username=username, password=password)
        if user is not None:
            auth.login(request, user)
            return redirect("home")
        else:
            messages.error(request, "Invalid credentials")
            return render(request, "login.html")
    return render(request, "login.html")


def logout(request):
    auth.logout(request)
    return redirect("login")


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]
        password = request.POST["password"]
        password_confirm = request.POST["password_confirm"]

        if password == password_confirm:
            try:
                user = User.objects.create_user(username, email, password)
                user.save()
                auth.login(request, user)
                return redirect("home")
            except:
                messages.error(request, "Error creating user")
                return render(request, "register.html")
        else:
            messages.error(request, "Passwords do not match")
            return render(request, "register.html")

    return render(request, "register.html")


@login_required
def user_settings(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        current_password = request.POST.get("current_password")
        new_password = request.POST.get("new_password")
        new_password_confirm = request.POST.get("new_password_confirm")

        user = request.user
        if not user.check_password(current_password):
            messages.error(request, "Incorrect password.")
            return redirect("user_settings")

        # Check if the form is empty
        if not any([username, email, new_password]):
            messages.warning(request, "Nothing to change.")
            return redirect("user_settings")

        if username:
            user.username = username
        if email:
            user.email = email
        if new_password:
            if new_password == new_password_confirm:
                user.set_password(new_password)
            else:
                messages.error(request, "New Password does not match.")
                return redirect("user_settings")

        user.save()
        update_session_auth_hash(request, user)  # Important!
        messages.success(request, "Your account has been updated!")
        return redirect("user_settings")

    return render(request, "user-settings.html")


def mymodels(request):
    if request.method == "POST":
        file = request.FILES["file"]
        response = utils.upload_file(file, "models")
        if response.status_code == 201:
            messages.success(request, "Model uploaded successfully")
            model_name = os.path.splitext(file.name)[0]
            thumbnails = _get_thumbnails([model_name], "models", gallery=False)
            if all(thumbnail["image"] is not None for thumbnail in thumbnails):
                base64_thumbnails = list(thumbnail["image"] for thumbnail in thumbnails)
                tags, categories, colors = _get_suggested_tags(base64_thumbnails)
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

    gallery_thumbnails = _get_all_thumbnails("models")
    return render(request, "mymodels.html", {"thumbnails": gallery_thumbnails})


def mymodel_detail(request, name):
    model_details = {
        "name": name,
        "thumbnails": [],
        "configuration": {},
    }

    thumbnails = _get_thumbnails([name], "models", gallery=False)

    for thumbnail in thumbnails:
        model_details["thumbnails"].append(thumbnail["image"])
    model_details["configuration"] = _get_model_configuration(name)

    return render(request, "mymodel_detail.html", {"asset": model_details})


def find_models(request):
    # Check if there is a search query via GET
    search = request.GET.get("search", "")
    fuel_models = []
    blendkit_models = []

    if search:
        search_results = _search_and_cache(search)

        for result in search_results["fuel"]:
            fuel_model_details = _get_fuel_model_details(result)
            fuel_models.append(fuel_model_details)

        for result in search_results["blendkit"]:
            blendkit_model_details = _get_blendkit_model_details(result)
            blendkit_models.append(blendkit_model_details)
    context = {
        "search": search,
        "fuel_models": fuel_models,
        "blendkit_models": blendkit_models,
    }
    return render(request, "find-models.html", context=context)


def add_to_my_models(request):
    if request.method == "POST":

        name = request.POST.get("name")
        if request.POST.get("library") == "fuel":
            owner = request.POST.get("owner")
            response = __add_fuel_model_to_my_models(name, owner)
        elif request.POST.get("library") == "blendkit":
            thumbnail = request.POST.get("thumbnail")
            asset_base_id = request.POST.get("assetBaseId")
            response = __add_blendkit_model_to_my_models(name, asset_base_id, thumbnail)
        if response.status_code == 201:
            response_data = {"message": f"Success: Model: {name} added to My Models"}
        else:
            response_data = {"error": f"Failed to add model: {name} to My Models"}
        return JsonResponse(response_data, status=response.status_code)
    else:
        return JsonResponse({"error": "Invalid request method"}, status=405)


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


def myrobot_detail(request, name):
    robot_details = {
        "name": name,
        "thumbnails": [],
    }

    thumbnails = _get_thumbnails([name], "robots", gallery=False)

    for thumbnail in thumbnails:
        robot_details["thumbnails"].append(thumbnail["image"])

    return render(request, "myrobot_detail.html", {"asset": robot_details})


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

        file = "index.json"
        response = utils.make_get_request(file)
        if response.status_code == 200:
            # Convert the JSON response to a dictionary
            index = json.loads(response.content)
        elif response.status_code == 404:
            index = {}
        else:
            messages.error(request, "Failed to fetch index.json")
            return redirect("mymodels")

        url_safe_name = urllib.parse.quote(name)
        index[name] = {
            "tags": tags,
            "categories": categories,
            "colors": colors,
            "url": utils.FILESERVER_URL + f"models/{url_safe_name}/?zip=true",
        }

        # The PUT will actually make an index.json the first time
        # around as well, so a POST to create is not needed.
        response = utils.make_put_request(file, data=json.dumps(index))
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
