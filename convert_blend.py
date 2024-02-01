import argparse
from dataclasses import dataclass
import yaml
import os
import shutil
import requests
import json
from pathlib import Path
from dotenv import load_dotenv
from roboprop_client.export_model import export_sdf

load_dotenv()

FILESERVER_URL = os.getenv("FILESERVER_URL", "")


def _send_request(endpoint, method, data=None, files=None):
    url = FILESERVER_URL + endpoint
    headers = {"X-DreamFactory-Api-Key": os.getenv("FILESERVER_API_KEY", "")}
    if method == "GET":
        response = requests.get(url, headers=headers)
    elif method == "PUT":
        response = requests.put(url, data=json.dumps(data), headers=headers)
    elif method == "POST":
        response = requests.post(url, files=files, headers=headers, timeout=60)
    return response  # type: ignore


def _add_model_metadata(config):
    endpoint = "files/index.json"
    response = _send_request(endpoint, "GET")
    if response.status_code == 200:
        index = json.loads(response.content)
        model_name = config.roboprop_key
        model_metadata = config.metadata
        model_metadata.update(
            {
                "source": "upload",
                "scale": 1.0,
                "url": FILESERVER_URL + f"files/models/{config.roboprop_key}/?zip=true",
            }
        )
        index[model_name] = model_metadata
        response = _send_request(endpoint, "PUT", index)
        if response.status_code == 201:
            return f"{model_name} uploaded to Roboprop and Metadata added successfully"
        else:
            return f"Error updating metadata for {model_name}: {response.content}"


def _upload_model_to_roboprop(args, config):
    model_folder = Path(args.out) / config.roboprop_key
    zip_file = config.roboprop_key
    shutil.make_archive(zip_file, "zip", model_folder)
    with open(f"{zip_file}.zip", "rb") as zip_file:
        files = {"files": (zip_file.name, zip_file)}
        endpoint = f"files/models/{config.roboprop_key}/?extract=true&clean=true"
        response = _send_request(endpoint, "POST", files=files)
    if response.status_code == 201:
        print(
            f"{config.roboprop_key} uploaded to Roboprop successfully, adding Metadata"
        )
        result = _add_model_metadata(config)
    else:
        result = f"Error uploading {config.roboprop_key}: {response.content}"
    return result


@dataclass
class Config:
    roboprop_key: str
    blend_file: Path
    metadata: dict

    @classmethod
    def from_yaml(cls, path: Path):
        with open(path) as f:
            config = yaml.safe_load(f)
            # validate config
            assert config is not None, "roboprop.yaml is empty"
            assert "roboprop_key" in config, "roboprop_key is missing in roboprop.yaml"
            assert "blend_file" in config, "blend_file is missing in roboprop.yaml"

            return Config(
                roboprop_key=config["roboprop_key"],
                blend_file=config["blend_file"],
                metadata=config.get("metadata", {}),
            )


def main():
    parser = argparse.ArgumentParser(
        description="Convert .blend file to model format using the roboprop.yaml config"
    )
    parser.add_argument(
        "roboprop_file", type=str, help="Path to the roboprop.yaml file"
    )
    parser.add_argument(
        "--out",
        type=str,
        default="./models",
        help="Output path",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        default=False,
        help="Upload the result to RoboProp",
    )

    args = parser.parse_args()
    roboprop_file = Path(args.roboprop_file)

    # read roboprop.yaml
    config = Config.from_yaml(roboprop_file)
    print(f"Config:\n{config}")

    export_sdf(
        out_dir=Path(args.out) / config.roboprop_key,
        model_name=config.roboprop_key,
        blend_file_path=roboprop_file.parent / config.blend_file,
    )

    if args.upload:
        result = _upload_model_to_roboprop(args, config)
        print(result)


if __name__ == "__main__":
    main()
