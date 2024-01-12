import argparse
from dataclasses import dataclass
import yaml
import os
import shutil
import requests
from pathlib import Path
from dotenv import load_dotenv
from roboprop_client.export_model import export_sdf

load_dotenv()

@dataclass
class Config:
    roboprop_key: str
    blend_file: Path
    # TODO add description and other fields needed for RoboProp models

    @classmethod
    def from_yaml(cls, path: Path):
        with open(path) as f:
            config = yaml.safe_load(f)
            # validate config
            assert "roboprop_key" in config, "roboprop_key is missing in roboprop.yaml"
            assert "blend_file" in config, "blend_file is missing in roboprop.yaml"

            return Config(
                roboprop_key=config["roboprop_key"],
                blend_file=config["blend_file"],
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
        default="/home/azazdeaz/repos/art-e-fact/RoboProp/models",
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
        # Define the directory to be zipped and the output zip file name
        model_folder = Path(args.out) / config.roboprop_key
        zip_file = config.roboprop_key
        shutil.make_archive(zip_file, 'zip', model_folder)
        with open(f"{zip_file}.zip", "rb") as zip_file:
            files = {"files": (zip_file.name, zip_file)}
            url = os.getenv("FILESERVER_URL", "") + f"models/{config.roboprop_key}/" + "?extract=true&clean=true"
            # At present all files are uploaded as a zip file.
            response = requests.post(
                url,
                files=files,
                headers={"X-DreamFactory-Api-Key": os.getenv("FILESERVER_API_KEY", "") },
                timeout=60,
            )
    
        if response.status_code == 201:
            print(f"{config.roboprop_key} uploaded successfully")

if __name__ == "__main__":
    main()
