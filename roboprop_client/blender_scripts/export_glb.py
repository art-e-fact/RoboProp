import bpy
from collisions import create_collision_model
from pathlib import Path


def _export(blend_file: Path, output: Path, format: str, collision_output: Path):
    # Reset the state of Blender
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # Load the blend file
    bpy.ops.wm.open_mainfile(filepath=str(blend_file))
    if format == "GLTF_SEPARATE":
        # Move texture images to external files so the exporter can copy them next to the model
        bpy.ops.file.unpack_all(method="USE_LOCAL")
    # Export GLB
    bpy.ops.export_scene.gltf(
        filepath=str(output),
        check_existing=False,
        use_selection=False,
        export_materials="EXPORT",
        export_format=format,
        export_image_format="JPEG",
        export_jpeg_quality=60,
        export_extras=True,
        # the export rigged models in pos, export_def_bones=True and export_rest_position_armature=False are needed
        export_rest_position_armature=False,
        # export_hierarchy_flatten_bones=True,
        export_def_bones=True,
    )

    create_collision_model()
    # Export the collision model
    bpy.ops.export_scene.gltf(
        filepath=str(collision_output),
        check_existing=False,
        use_selection=False,
        export_materials="EXPORT",
        export_format=format,  # Use the format parameter
        export_image_format="JPEG",
        export_jpeg_quality=60,
        export_extras=True,
        export_def_bones=True,
    )


def export_glb(blend_file: Path, output: Path):
    _export(blend_file, output, "GLB")


def export_gltf(blend_file: Path, output: Path):
    _export(blend_file, output, "GLTF_SEPARATE")
