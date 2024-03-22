import bpy

def create_collision_model():
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
