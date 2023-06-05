import os
import requests
import base64
from django.shortcuts import render
from django.http import HttpResponse

headers = {"X-DreamFactory-API-Key": os.getenv("FILESERVER_API_KEY")}
fileserver_url = os.getenv("FILESERVER_URL")


def _get_assets(asset_library):
    if asset_library == "roboprop":
        url = fileserver_url + "?full_tree=true&as_list=true"
        response = requests.get(url, headers=headers)
        data = response.json()["resource"]
    return data


def _get_roboprop_asset_thumbnails(assets):
    thumbnails = {}
    for asset in assets:
        if "thumbnails" in asset and not asset.endswith("/"):
            name = asset.split("/")[0]
            url = fileserver_url + asset + "?is_base64=true"
            response = requests.get(url, headers=headers)
            thumbnail_base64 = base64.b64encode(response.content).decode("utf-8")
            # Ensure only one thumbnail per asset
            if name not in thumbnails:
                thumbnails[name] = thumbnail_base64
    return [
        {"name": name, "thumbnail": thumbnail_base64}
        for name, thumbnail_base64 in thumbnails.items()
    ]


def home(request):
    roboprop_assets = _get_assets("roboprop")
    roboprop_asset_thumbnails = _get_roboprop_asset_thumbnails(roboprop_assets)
    fuel_thumbnails = []  # TODO:
    thumbnails = roboprop_asset_thumbnails + fuel_thumbnails

    return render(request, "home.html", {"thumbnails": thumbnails})
