import requests
import os

FILESERVER_API_KEY = "X-DreamFactory-API-Key"
FILESERVER_API_KEY_VALUE = os.getenv("FILESERVER_API_KEY", "")


# FILESERVER REQUESTS
def make_get_request(url):
    return requests.get(url, headers={FILESERVER_API_KEY: FILESERVER_API_KEY_VALUE})


def make_put_request(url, data):
    response = requests.put(
        url,
        data=data,
        headers={FILESERVER_API_KEY: FILESERVER_API_KEY_VALUE},
    )
    response.raise_for_status()


def make_post_request(url, files=None):
    if files:
        response = requests.post(
            url,
            files=files,
            headers={FILESERVER_API_KEY: FILESERVER_API_KEY_VALUE},
            timeout=30,
        )
    else:
        response = requests.post(
            url,
            headers={FILESERVER_API_KEY: FILESERVER_API_KEY_VALUE},
        )

    return response


# A generic function that takes a dictionary with keys
# that are dot-separated and converts them into nested dictionaries.
# e.g {"a.b": 1} becomes {"a": {"b": 1}}
def unflatten_dict(dictionary):
    result = {}
    for key, value in dictionary.items():
        if "." in key:
            parts = key.split(".")
            sub_dict = result
            for part in parts[:-1]:
                if part not in sub_dict:
                    sub_dict[part] = {}
                sub_dict = sub_dict[part]
            sub_dict[parts[-1]] = value
        else:
            result[key] = value
    return result


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
