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

# Add Palanar Decimate modifyer to all meshes
angle_limit = 12.0  # merge faces within this angle
for obj in bpy.data.objects:
    if obj.type == "MESH":
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_add(type="DECIMATE")
        modifier = bpy.context.object.modifiers[-1]
        modifier.decimate_type = "DISSOLVE"
        modifier.angle_limit = angle_limit / 180.0 * 3.14159
        bpy.ops.object.modifier_apply(modifier=modifier.name)

bpy.ops.export_scene.gltf(
    filepath=args.output,
    check_existing=False,
    use_selection=False,
    export_materials="EXPORT",
    export_format="GLB",
    export_image_format="JPEG",
    export_jpeg_quality=60,
)
