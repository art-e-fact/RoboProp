import requests
import os
import shutil
import zipfile

FILESERVER_API_KEY = "X-DreamFactory-API-Key"
FILESERVER_API_KEY_VALUE = os.getenv("FILESERVER_API_KEY", "")
FILESERVER_URL = os.getenv("FILESERVER_URL", "")
BLENDERKIT_PRO_API_KEY = os.getenv("BLENDERKIT_PRO_API_KEY", "")


# FILESERVER REQUESTS
def make_get_request(url):
    url = FILESERVER_URL + url
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
