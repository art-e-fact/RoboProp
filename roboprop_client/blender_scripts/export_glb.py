import bpy
from pathlib import Path
import argparse
import sys

parser = argparse.ArgumentParser()
parser.add_argument("-o", "--output", dest="output", required=True)


if "--" in sys.argv:
    argv = sys.argv[sys.argv.index("--") + 1 :]
else:
    argv = []
args = parser.parse_known_args(argv)[0]

bpy.ops.export_scene.gltf(
    filepath=args.output,
    check_existing=False,
    use_selection=False,
    export_materials="EXPORT",
    export_format="GLB",
    export_image_format="JPEG",
    export_jpeg_quality=88,
)
