import bpy
from pathlib import Path


def export_obj(blend_file: Path, output: Path):
    # Reset the state of Blender
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # Load the blend file
    bpy.ops.wm.open_mainfile(filepath=str(blend_file))
    # Move texture images to external files so the exporter can copy them next to the model
    bpy.ops.file.unpack_all(method="USE_LOCAL")
    # Export OBJ
    bpy.ops.wm.obj_export(
        filepath=str(output),
        check_existing=False,
        export_selected_objects=False,
        export_uv=True,
        export_normals=True,
        export_colors=True,
        export_materials=True,
        export_pbr_extensions=True,
        # copy all the texture images next to the model
        path_mode="COPY",
        export_triangulated_mesh=True,
        export_object_groups=True,
        export_material_groups=True,
    )
