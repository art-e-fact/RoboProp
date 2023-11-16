import bpy
from pathlib import Path
import argparse
import sys
import os

parser = argparse.ArgumentParser()
parser.add_argument("-o", "--output", dest="output", required=True)


if "--" in sys.argv:
    argv = sys.argv[sys.argv.index("--") + 1 :]
else:
    argv = []
args = parser.parse_known_args(argv)[0]
output = Path(args.output)

# Add Palanar Decimate modifyer to all meshes
# angle_limit = 12.0  # merge faces within this angle
# for obj in bpy.data.objects:
#     if obj.type == "MESH":
#         bpy.context.view_layer.objects.active = obj
#         bpy.ops.object.modifier_add(type="DECIMATE")
#         modifier = bpy.context.object.modifiers[-1]
#         modifier.decimate_type = "DISSOLVE"
#         modifier.angle_limit = angle_limit / 180.0 * 3.14159
#         bpy.ops.object.modifier_apply(modifier=modifier.name)

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
