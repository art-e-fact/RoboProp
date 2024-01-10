import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(
    filepath="/home/azazdeaz/repos/art-e-fact/urdfs/roboprop/BumerangChair/assets/visual.glb",
    files=[{"name": "visual.glb", "name": "visual.glb"}],
    loglevel=50,
)
bpy.ops.file.unpack_all(method='WRITE_LOCAL')
bpy.ops.wm.obj_export(
    filepath="/home/azazdeaz/repos/art-e-fact/urdfs/roboprop/BumerangChair/assets/gen/visual.obj",
    check_existing=False,
    # # Use ROS coordinate frame
    # axis_forward="X",
    # axis_up="Z",
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