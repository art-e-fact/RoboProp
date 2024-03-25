import os
from xml.dom import minidom
from xml.etree import ElementTree
from pathlib import Path
from roboprop_client.blender_scripts.export_glb import export_glb, export_gltf
from roboprop_client.blender_scripts.export_fbx import export_fbx
from roboprop_client.blender_scripts.export_obj import export_obj

EXPORT_CONFIGS = [
    {
        "visual": "assets/visual.fbx",
        "collision": "assets/collision.fbx",
        "sdf": "model.sdf",
        "config": "model.config",
    },
    {
        "visual": "assets/visual.glb",
        "collision": "assets/collision.glb",
        "sdf": "glft-model.sdf",
        "config": "glft-model.config",
    },
]


# Util for saving an XML file
def write_xml(xml: ElementTree.Element, filepath: Path):
    xml_string = minidom.parseString(
        ElementTree.tostring(xml, encoding="unicode")
    ).toprettyxml(indent="  ")
    file = open(filepath, "w")
    file.write(xml_string)
    file.close()
    print(f"Saved: {filepath}")


def export_sdf(out_dir: Path, model_name: str, blend_file_path: Path):
    sdf_version = "1.9"

    for export_config in EXPORT_CONFIGS:
        visual_path = out_dir / export_config["visual"]
        collision_path = out_dir / export_config["collision"]
        sdf_path = out_dir / export_config["sdf"]
        config_path = out_dir / export_config["config"]

        # Export visual model
        os.makedirs(name=os.path.dirname(visual_path), exist_ok=True)
        if Path(visual_path).suffix == ".fbx":
            export_fbx(blend_file_path, visual_path, collision_path)
        elif Path(visual_path).suffix == ".glb":
            export_glb(blend_file_path, visual_path, collision_path)
        elif Path(visual_path).suffix == ".gltf":
            export_gltf(blend_file_path, visual_path, collision_path)
        elif Path(visual_path).suffix == ".obj":
            export_obj(blend_file_path, visual_path, collision_path)
        else:
            raise ValueError(
                f"Exporting models the with extension '{Path(visual_path).suffix}' is not implemented yet. (Appears in {visual_path})"
            )

        print(f"Saved {visual_path}")

        # Generate SDF
        sdf = ElementTree.Element("sdf", attrib={"version": sdf_version})
        model = ElementTree.SubElement(sdf, "model", attrib={"name": model_name})
        static_xml = ElementTree.SubElement(model, "static")
        static_xml.text = str(False)
        link = ElementTree.SubElement(
            model, "link", attrib={"name": f"{model_name}_link"}
        )

        link.append(
            ElementTree.Comment(
                "Convert model orientations from right-handed y-up z-back to ROS"
            )
        )
        pose = ElementTree.SubElement(link, "pose")
        pose.set("degrees", "1")
        pose.text = "0 0 0 90 0 -90"

        visual = ElementTree.SubElement(
            link, "visual", attrib={"name": f"{model_name}_visual"}
        )
        visual_geometry = ElementTree.SubElement(visual, "geometry")
        visual_mesh = ElementTree.SubElement(visual_geometry, "mesh")
        visual_mesh_uri = ElementTree.SubElement(visual_mesh, "uri")
        visual_mesh_uri.text = os.path.relpath(visual_path, os.path.dirname(sdf_path))
        collision = ElementTree.SubElement(
            link, "collision", attrib={"name": f"{model_name}_collision"}
        )
        collision_geometry = ElementTree.SubElement(collision, "geometry")
        collision_mesh = ElementTree.SubElement(collision_geometry, "mesh")
        collision_mesh_uri = ElementTree.SubElement(collision_mesh, "uri")
        collision_mesh_uri.text = os.path.relpath(
            collision_path, os.path.dirname(sdf_path)
        )

        write_xml(sdf, sdf_path)

        # Generate a minimal config file. For more options, see: https://github.com/gazebosim/gz-sim/blob/a738dec47ae4f5c18f48a6d4d4b0edb500a490fa/examples/scripts/blender/procedural_dataset_generator.py#L1161-L1211
        model_config = ElementTree.Element("model")
        name = ElementTree.SubElement(model_config, "name")
        name.text = model_name

        # Path to SDF
        sdf_tag = ElementTree.SubElement(
            model_config, "sdf", attrib={"version": sdf_version}
        )
        sdf_tag.text = os.path.relpath(sdf_path, os.path.dirname(config_path))

        write_xml(model_config, config_path)
