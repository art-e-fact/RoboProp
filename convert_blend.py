import argparse
from dataclasses import dataclass
import yaml
from pathlib import Path
from roboprop_client.export_model import export_sdf


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

    # TODO: upload to RoboProp


if __name__ == "__main__":
    main()
