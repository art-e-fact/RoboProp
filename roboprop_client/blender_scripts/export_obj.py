import bpy
from pathlib import Path
import argparse
import sys
import os

parser = argparse.ArgumentParser()
parser.add_argument('-o', '--output', dest='output', required=True)


if '--' in sys.argv:
    argv = sys.argv[sys.argv.index('--') + 1:]
else:
    argv = []
args = parser.parse_known_args(argv)[0]
output = Path(args.output)

bpy.ops.file.unpack_all(method="USE_LOCAL")

bpy.ops.export_scene.obj(
    filepath=args.output,
    check_existing=False,
    # Use ROS coordinate frame
    axis_forward="Y",
    axis_up="Z",
    use_selection=False,
    use_materials=True,
    use_triangles=True,
    # copy all the texture images next to the model
    path_mode="COPY",
)
