import requests
import os
import shutil
import zipfile
import urllib.parse
import json
from roboprop_client.load_blenderkit import load_blenderkit_model

FILESERVER_API_KEY = "X-DreamFactory-API-Key"
FILESERVER_API_KEY_VALUE = os.getenv("FILESERVER_API_KEY", "")
FILESERVER_URL = os.getenv("FILESERVER_URL", "")
BLENDERKIT_PRO_API_KEY = os.getenv("BLENDERKIT_PRO_API_KEY", "")


# FILESERVER REQUESTS
def make_get_request(url, session_token=None):
    url = FILESERVER_URL + url
    if session_token:
        return requests.get(
            url,
            headers={
                FILESERVER_API_KEY: FILESERVER_API_KEY_VALUE,
                "X-DreamFactory-Session-Token": session_token,
            },
        )
    else:
        return requests.get(url, headers={FILESERVER_API_KEY: FILESERVER_API_KEY_VALUE})


def make_put_request(url, data):
    url = FILESERVER_URL + url
    response = requests.put(
        url,
        data=data,
        headers={FILESERVER_API_KEY: FILESERVER_API_KEY_VALUE},
    )
    return response


def make_post_request(
    url, parameters="?extract=true&clean=true", files=None, json=None
):
    url = FILESERVER_URL + url + parameters
    if files:
        # At present all files are uploaded as a zip file.
        response = requests.post(
            url,
            files=files,
            headers={FILESERVER_API_KEY: FILESERVER_API_KEY_VALUE},
            timeout=60,
        )
    elif json:
        response = requests.post(
            url,
            headers={FILESERVER_API_KEY: FILESERVER_API_KEY_VALUE},
            json=json,
        )
    else:
        response = requests.post(
            url,
            headers={FILESERVER_API_KEY: FILESERVER_API_KEY_VALUE},
        )
    return response


def make_delete_request(url, session_token=None):
    url = FILESERVER_URL + url
    if session_token:
        return requests.delete(
            url,
            headers={
                FILESERVER_API_KEY: FILESERVER_API_KEY_VALUE,
                "X-DreamFactory-Session-Token": session_token,
            },
        )
    else:
        return requests.delete(
            url, headers={FILESERVER_API_KEY: FILESERVER_API_KEY_VALUE}
        )


def upload_file(file, asset_type):
    files = {"files": (file.name, file.read())}
    asset_name = os.path.splitext(file.name)[0]
    # Creates the folder as well as unzipping the model into it.
    url = f"{asset_type}/{asset_name}/"
    response = make_post_request(url, files=files)
    return response


# A generic function that takes a dictionary of dictionaries
# and dot-seperates them. e.g. {"a": {"b": 1}} becomes {"a.b": 1}
def flatten_dict(dictionary, parent_key="", sep="."):
    items = []
    for key, value in dictionary.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else key
        if isinstance(value, dict):
            items.extend(flatten_dict(value, new_key, sep=sep).items())
        else:
            items.append((new_key, value))
    return dict(items)


def create_list_from_string(comma_separated_string):
    if not comma_separated_string:
        return []
    else:
        substrings = comma_separated_string.split(",")
        stripped_substrings = [substring.lstrip().rstrip() for substring in substrings]
        return stripped_substrings


def capitalize_and_remove_spaces(string):
    words = string.split()
    capitalized_words = [word.capitalize() for word in words]
    return "".join(capitalized_words)


def create_zip_file(folder_name):
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

    return zip_filename, zip_path


def delete_folders(folders):
    for folder in folders:
        if os.path.exists(folder):
            shutil.rmtree(folder)


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
    zip_filename, zip_path = create_zip_file(folder_name)
    # Upload the ZIP file in a POST request
    with open(zip_path, "rb") as zip_file:
        files = {"files": (zip_filename, zip_file)}
        asset_name = os.path.splitext(zip_filename)[0]
        url = f"files/models/{asset_name}/"
        response = make_post_request(url, files=files)

    delete_folders(["models", "textures"])
    return response


def _get_blenderkit_metadata(folder_name):
    tags = []
    categories = []
    description = []
    url = f"files/models/{folder_name}/blenderkit_meta.json"
    response = make_get_request(url)
    if response.status_code == 200:
        metadata = response.json()
        tags = metadata.get("tags", [])
        # Blenderkit has only one category per model, but this
        # is a list for consistency
        categories = [metadata.get("category", "").strip()]
        description = metadata.get("description", "")
    return tags, categories, description


def _update_index(request, model_name, model_metadata, model_source, index):
    url_safe_name = urllib.parse.quote(model_name)
    model_metadata["source"] = model_source
    model_metadata["scale"] = 1.0
    model_metadata["url"] = FILESERVER_URL + f"files/models/{url_safe_name}/?zip=true"
    index[model_name] = model_metadata
    response = make_put_request("files/index.json", data=json.dumps(index))
    return response


def _add_blenderkit_model_metadata(request, folder_name, asset_base_id, index):
    tags, categories, description = _get_blenderkit_metadata(folder_name)
    metadata = {
        "tags": tags,
        "categories": categories,
        "description": description,
        "assetBaseId": asset_base_id,
    }
    source = "Blenderkit_pro" if len(BLENDERKIT_PRO_API_KEY) > 0 else "Blenderkit"
    response = _update_index(request, folder_name, metadata, source, index)
    return response
