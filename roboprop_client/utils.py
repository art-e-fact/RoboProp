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
