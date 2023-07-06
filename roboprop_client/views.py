import requests
import base64
import xmltodict
import json
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
        "name": result["name"],
        "owner": result["owner"],
        "description": result["description"],
        "thumbnail": thumbnail_url,
    }


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
        response = utils.upload_file(request.FILES["file"], "models")
        if response.status_code == 201:
            messages.success(request, "Model uploaded successfully")
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
        url = f"models/{name}/"
        parameters = f"?url=https://fuel.gazebosim.org/1.0/{owner}/models/{name}.zip&extract=true&clean=true"
        response = utils.make_post_request(url, parameters=parameters)
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
