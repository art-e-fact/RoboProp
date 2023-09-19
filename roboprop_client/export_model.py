import os
from xml.dom import minidom
from xml.etree import ElementTree
from pathlib import Path
import subprocess

# COLLISION_EXTENSION = ".stl"
OBJECT_TYPES = [["default", ".obj"], ["gltf", ".glb"]]


def export_sdf(path_model: Path, model_name: str, blend_file_path: str):
    # path_collision = os.path.join(path_model, f"assets/collision{COLLISION_EXTENSION}")
    visual_paths = [
        os.path.join(path_model, f"assets/visual{ext}") for _, ext in OBJECT_TYPES
    ]
    sdf_paths = [
        os.path.join(
            path_model, "model.sdf" if sim == "default" else f"{sim}-model.sdf"
        )
        for sim, _ in OBJECT_TYPES
    ]
    config_paths = [
        os.path.join(
            path_model, "model.config" if sim == "default" else f"{sim}-model.config"
        )
        for sim, _ in OBJECT_TYPES
    ]
    sdf_version = "1.9"

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
        for path_sdf, path_visual in zip(sdf_paths, visual_paths):
            sdf = ElementTree.Element("sdf", attrib={"version": sdf_version})
            model = ElementTree.SubElement(sdf, "model", attrib={"name": model_name})
            static_xml = ElementTree.SubElement(model, "static")
            static_xml.text = str(False)
            link = ElementTree.SubElement(
                model, "link", attrib={"name": f"{model_name}_link"}
            )

            visual = ElementTree.SubElement(
                link, "visual", attrib={"name": f"{model_name}_visual"}
            )
            visual_geometry = ElementTree.SubElement(visual, "geometry")
            visual_mesh = ElementTree.SubElement(visual_geometry, "mesh")
            visual_mesh_uri = ElementTree.SubElement(visual_mesh, "uri")
            visual_mesh_uri.text = os.path.relpath(
                path_visual, os.path.dirname(path_sdf)
            )
            collision = ElementTree.SubElement(
                link, "collision", attrib={"name": f"{model_name}_collision"}
            )
            collision_geometry = ElementTree.SubElement(collision, "geometry")
            collision_mesh = ElementTree.SubElement(collision_geometry, "mesh")
            collision_mesh_uri = ElementTree.SubElement(collision_mesh, "uri")
            collision_mesh_uri.text = os.path.relpath(
                path_visual, os.path.dirname(path_sdf)
            )

            write_xml(sdf, path_sdf)

    # Generate a minimal config file. For more options, see: https://github.com/gazebosim/gz-sim/blob/a738dec47ae4f5c18f48a6d4d4b0edb500a490fa/examples/scripts/blender/procedural_dataset_generator.py#L1161-L1211
    def generate_config():
        for path_sdf, path_config in zip(sdf_paths, config_paths):
            model_config = ElementTree.Element("model")
            name = ElementTree.SubElement(model_config, "name")
            name.text = model_name

            # Path to SDF
            sdf_tag = ElementTree.SubElement(
                model_config, "sdf", attrib={"version": sdf_version}
            )
            sdf_tag.text = os.path.relpath(path_sdf, os.path.dirname(path_config))

            write_xml(model_config, path_config)

    def export_model(with_materials: bool):
        def run_export(export_script):
            cmd = [
                "blender",
                blend_file_path,
                "--background",
                "--factory-startup",
                "--python",
                Path(__file__).parent / "blender_scripts" / export_script,
                "--",
                "--output",
                path_visual,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)

        for path_visual in visual_paths:
            os.makedirs(name=os.path.dirname(path_visual), exist_ok=True)
            if Path(path_visual).suffix == ".obj":
                run_export("export_obj.py")
            elif Path(path_visual).suffix == ".glb":
                run_export("export_glb.py")
            else:
                raise ValueError(
                    f"Exporting models the with extension '{Path(path_visual).suffix}' is not implemented yet. (Appears in {path_visual})"
                )

        print(f"Saved {path_visual}")

    export_model(with_materials=True)

    # Create the model.sdf file
    generate_sdf()
    # Create the model.config file
    generate_config()
