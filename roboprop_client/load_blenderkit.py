import uuid
from pathlib import Path
import requests
import sys
import os
import argparse
import sys
import json
import roboprop_client.utils as utils

# Trick to allow importing from the same directory in Blender
script_dir = os.path.dirname(os.path.realpath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

from export_model import export_sdf

CACHE_PATH = Path(".cache")


def download_large_file(url, destination):
    response = requests.get(url, stream=True)
    response.raise_for_status()  # Ensure we got an OK response

    with open(destination, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            # If you have chunk encoded response uncomment if
            # and set chunk_size parameter to None.
            # if chunk:
            f.write(chunk)


def load_asset_meta(asset_base_id: str):
    # Load asset meta data
    url_path = (
        f"https://www.blenderkit.com/api/v1/search/?query=asset_base_id:{asset_base_id}"
    )
    response = requests.get(url_path)
    data = response.json()
    if data["count"] == 0 or data["count"] > 1:
        return
    return data["results"][0]


def load_model_from_blenderkit(meta):
    asset_id = meta["id"]

    # Create output directory
    output_folder = CACHE_PATH / asset_id
    output_folder.mkdir(exist_ok=True, parents=True)
    # Set temp path for downloading. This allows clean stop and continue of the script
    temp_path = output_folder / "temp.blend"

    output_path = output_folder / "model.blend"
    if output_path.exists():
        return output_path

    # Try to find url to blend file
    download_url = None
    for file in meta["files"]:
        if file["fileType"] == "blend":
            download_url = file["downloadUrl"]

    if download_url is None:
        return

    # Create a random scene uuid which is necessary for downloading files
    scene_uuid = str(uuid.uuid4())

    download_url = download_url + "?scene_uuid=" + scene_uuid
    # Download metadata for blend file
    if len(utils.BLENDERKIT_PRO_API_KEY) == 0:
        # Can only use free models, so no API key is needed
        response = requests.get(download_url)
    else:
        # Having an API key = having a subscription
        response = requests.get(
            download_url,
            headers={"Authorization": "Bearer " + utils.BLENDERKIT_PRO_API_KEY},
        )
    data = response.json()
    # Extract actual download path
    file_path = data["filePath"]
    # Download the file
    download_large_file(file_path, str(temp_path))
    temp_path.rename(output_path)
    return output_path


def add_demo_world(model_path: Path):
    with open("roboprop_client/demo.sdf.template", "r") as template_file:
        template = template_file.read()

    output_text = template.replace("{{model_path}}", str(model_path))

    demo_path = model_path / "demo.sdf"
    with open(demo_path, "w") as f:
        f.write(output_text)

    return demo_path


def load_blenderkit_model(asset_base_id: str, output_path: str, model_name: str = None):
    # Load asset meta data from BlenderKit
    meta = load_asset_meta(asset_base_id)

    if not model_name:
        model_name = meta["name"]

    blend_file = load_model_from_blenderkit(meta)
    model_path = Path(output_path) / model_name
    # objs = bproc.loader.load_blend(blend_file)
    # bpy.ops.wm.open_mainfile(filepath=blend_file)
    # bpy.ops.file.unpack_all(method="USE_LOCAL")
    export_sdf(model_path, model_name, blend_file)

    # Save meta data in the model folder
    meta_path = model_path / "blenderkit_meta.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=4)

    demo_path = add_demo_world(model_path)


def main(args):
    load_blenderkit_model(args.asset_base_id, args.output_path, args.model_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="""
        CLI app for converting BlenderKit models to (Gazebo) SDF
        Example usage:
          python roboprop_client/load_blenderkit.py --asset_base_id 42f9e34f-f817-4505-b000-f86be1a68c8b --output_path models --model_name StrangeChair
        """
    )

    parser.add_argument(
        "--asset_base_id",
        type=str,
        required=True,
        help="The UUID you find in the blenderkit.com URL and on the model page",
    )

    parser.add_argument(
        "--output_path",
        type=str,
        required=True,
        help='The path where the output model will be saved (like "path/to/models")',
    )

    parser.add_argument(
        "--model_name",
        type=str,
        help="The name of the model. Defaults to the model name on BlenderKit",
    )

    args = parser.parse_args()

    main(args)
