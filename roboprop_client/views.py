import os
import requests
import base64
from django.shortcuts import render
from django.http import HttpResponse


def home(request):
    api_key = os.getenv("FILESERVER_API_KEY")
    url = os.getenv("FILESERVER_URL") + "?full_tree=true&as_list=true"
    headers = {"X-DreamFactory-API-Key": api_key}
    response = requests.get(url, headers=headers)
    data = response.json()["resource"]
    thumbnails = []
    for item in data:
        if "thumbnails" in item and not item.endswith("/"):
            folder_name = item.split("/")[0]
            thumbnail_url = os.getenv("FILESERVER_URL") + item + "?is_base64=true"
            thumbnail_response = requests.get(thumbnail_url, headers=headers)
            thumbnail_data = thumbnail_response.content
            thumbnail_base64 = base64.b64encode(thumbnail_data).decode("utf-8")
            for folder in thumbnails:
                if folder_name == folder["folder_name"]:
                    folder["thumbnails"].append(thumbnail_base64)
                    break
            else:
                thumbnails.append(
                    {"folder_name": folder_name, "thumbnails": [thumbnail_base64]}
                )
    print(thumbnails)
    return render(request, "home.html", {"thumbnails": thumbnails})
