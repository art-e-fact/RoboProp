import bpy
from collisions import create_collision_model
from pathlib import Path


def export_fbx(blend_file: Path, output: Path, collision_output: Path):
    # Visual model
    # Reset the state of Blender
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # Load the blend file
    bpy.ops.wm.open_mainfile(filepath=str(blend_file))
    # Move texture images to external files so the exporter can copy them next to the model
    bpy.ops.file.unpack_all(method="USE_LOCAL")
    # Export FBX
    # https://docs.blender.org/api/current/bpy.ops.export_scene.html#module-bpy.ops.export_scene
    bpy.ops.export_scene.fbx(
        filepath=str(output),
        check_existing=False,
        object_types={"MESH"},
        path_mode="COPY",
        embed_textures=False,  # Gazebo can't handle embedded textures
        apply_scale_options="FBX_SCALE_ALL",
    )

    create_collision_model()
    # Export the collision model
    bpy.ops.export_scene.fbx(
        filepath=str(collision_output),
        check_existing=False,
        object_types={"MESH"},
        path_mode="COPY",
        embed_textures=False,
        use_mesh_modifiers=True,
        mesh_smooth_type="FACE",
        use_mesh_edges=False,
        use_tspace=False,
        use_custom_props=False,
        add_leaf_bones=False,
        primary_bone_axis="Y",
        secondary_bone_axis="X",
        use_armature_deform_only=True,
        bake_anim=False,
        use_metadata=False,
        apply_scale_options="FBX_SCALE_ALL",
        use_triangles=True,  # Convert all geometry to triangles
    )
