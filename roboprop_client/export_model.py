import bpy
import os
from xml.dom import minidom
from xml.etree import ElementTree
from pathlib import Path

VISUAL_EXTENSION = ".glb"
COLLISION_EXTENSION = ".stl"

def export_sdf(path_model: Path, model_name: str):
    path_collision = os.path.join(path_model, f"assets/collision{COLLISION_EXTENSION}")
    path_visual = os.path.join(path_model, f"assets/visual{VISUAL_EXTENSION}")
    path_sdf = os.path.join(path_model, "model.sdf")
    path_config = os.path.join(path_model, "model.config")
    sdf_version = "1.9"

    def separate_meshes_by_material(obj):
        all_objects_before = list(bpy.data.objects)
        ctx = bpy.context.copy()
        ctx["object"] = obj
        bpy.ops.mesh.separate(ctx, type="MATERIAL")
        new_objects = [o for o in bpy.data.objects if o not in all_objects_before]
        parts = [obj] + new_objects
        return parts

    # Util for duplicating a Blender object
    def duplicate(obj, add_to_scene=True):
        obj_copy = obj.copy()
        obj_copy.data = obj_copy.data.copy()
        if add_to_scene:
            bpy.context.scene.collection.objects.link(obj_copy)
        return obj_copy

    # Util for saving an XML file
    def write_xml(xml: ElementTree.Element, filepath: str):
        xml_string = minidom.parseString(
            ElementTree.tostring(xml, encoding="unicode")
        ).toprettyxml(indent="  ")
        file = open(filepath, "w")
        file.write(xml_string)
        file.close()
        print(f"Saved: {filepath}")

    def generate_sdf():
        sdf = ElementTree.Element("sdf", attrib={"version": sdf_version})
        model = ElementTree.SubElement(sdf, "model", attrib={"name": model_name})
        statit_xml = ElementTree.SubElement(model, "static")
        statit_xml.text = str(True)
        link = ElementTree.SubElement(
            model, "link", attrib={"name": f"{model_name}_link"}
        )

        visual = ElementTree.SubElement(
            link, "visual", attrib={"name": f"{model_name}_visual"}
        )
        visual_geometry = ElementTree.SubElement(visual, "geometry")
        visual_mesh = ElementTree.SubElement(visual_geometry, "mesh")
        visual_mesh_uri = ElementTree.SubElement(visual_mesh, "uri")
        visual_mesh_uri.text = os.path.relpath(path_visual, os.path.dirname(path_sdf))

        write_xml(sdf, path_sdf)

    # Generate a minimal config file. For more options, see: https://github.com/gazebosim/gz-sim/blob/a738dec47ae4f5c18f48a6d4d4b0edb500a490fa/examples/scripts/blender/procedural_dataset_generator.py#L1161-L1211
    def generate_config():
        model_config = ElementTree.Element("model")
        name = ElementTree.SubElement(model_config, "name")
        name.text = model_name

        # Path to SDF
        sdf_tag = ElementTree.SubElement(
            model_config, "sdf", attrib={"version": sdf_version}
        )
        sdf_tag.text = os.path.relpath(path_sdf, os.path.dirname(path_config))

        write_xml(model_config, path_config)

    def export_model(filepath: str, with_materials: bool):
        os.makedirs(name=os.path.dirname(filepath), exist_ok=True)
        bpy.ops.object.select_all(action="SELECT")
        if Path(filepath).suffix == ".obj":
            bpy.ops.export_scene.obj(
                filepath=filepath,
                check_existing=False,
                # Use ROS coordinate frame
                axis_forward="Y",
                axis_up="Z",
                use_selection=True,
                use_materials=with_materials,
                use_triangles=True,
                # copy all the texture images next to the model
                path_mode="COPY",
            )
        elif Path(filepath).suffix == ".glb":
            bpy.ops.export_scene.gltf(
                filepath=filepath,
                check_existing=False,
                use_selection=True,
                export_materials="EXPORT" if with_materials else "NONE",
                export_format='GLB',
                export_image_format='AUTO',
            )
        else:
            raise ValueError(f"Exporting models the with extension '{Path(filepath).suffix}' is not implemented yet. (Appears in {filepath})")
        
        print(f"Saved {filepath}")

    # Export mesh
    export_model(path_visual, with_materials=True)
    # TODO separate meshes and collect texture info
    # Delete the duplicated objects
    bpy.ops.object.delete()

    # Create the model.sdf file
    generate_sdf()
    # Create the model.config file
    generate_config()
