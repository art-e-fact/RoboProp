import bpy
from pathlib import Path

def _export(blend_file: Path, output: Path, format: str):
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
    )

def export_glb(blend_file: Path, output: Path):
    _export(blend_file, output, "GLB")

def export_gltf(blend_file: Path, output: Path):
    _export(blend_file, output, "GLTF_SEPARATE")