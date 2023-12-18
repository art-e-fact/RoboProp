import argparse
import os
from pathlib import Path
from roboprop_client.export_model import export_sdf


def main():
    parser = argparse.ArgumentParser(description="Convert .blend file to model format")
    parser.add_argument("blend_file", type=str, help="Path to the .blend file")
    parser.add_argument(
        "--name",
        type=str,
        default=None,
        help="Name of the model. Defaults to the name of the .blend file",
    )
    parser.add_argument("--out", type=str, default=None, help="Output path")
    parser.add_argument(
        "--upload",
        action="store_true",
        default=False,
        help="Upload the result to RoboProp",
    )

    args = parser.parse_args()

    if args.name is None:
        args.name = os.path.splitext(os.path.basename(args.blend_file))[0]

    export_sdf(
        out_dir=Path(args.out),
        model_name=args.name,
        blend_file_path=Path(args.blend_file),
    )


if __name__ == "__main__":
    main()
