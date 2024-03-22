import bpy
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

    # Collision model
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH":
            obj.data = obj.data.copy() # Make the mesh single user
            obj.shape_key_clear()  # Remove shape keys
            # Decimate modifier
            decimate_modifier = obj.modifiers.new("DecimateMod", "DECIMATE")
            decimate_modifier.ratio = 0.5  # Lower is simpler
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.object.modifier_apply(modifier=decimate_modifier.name)

            # Remesh modifier
            remesh_modifier = obj.modifiers.new("RemeshMod", "REMESH")
            remesh_modifier.mode = "SMOOTH"  # BLOCKS, SMOOTH, or SHARP
            remesh_modifier.octree_depth = 6  # Lower is simpler
            bpy.ops.object.modifier_apply(modifier=remesh_modifier.name)

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
