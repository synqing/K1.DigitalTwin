"""
build_environment_from_manifest.py

Generic loader: imports meshes from manifest into Blender.

Run from Blender via BlenderMCP:
  blender.execute_code(open('scripts/build_environment_from_manifest.py').read())

Or import and call:
  from build_environment_from_manifest import build_from_manifest
  build_from_manifest(Path('/path/to/manifest.json'))
"""

import json
from pathlib import Path

import bpy


def import_mesh(path: Path) -> bpy.types.Object:
    """Import mesh file (OBJ or GLB/GLTF) and return the main object."""
    ext = path.suffix.lower()

    # Store existing objects to find newly imported ones
    existing = set(bpy.data.objects.keys())

    if ext == ".obj":
        # Blender 4.0+ uses wm.obj_import
        try:
            bpy.ops.wm.obj_import(filepath=str(path))
        except AttributeError:
            # Fallback for older Blender versions
            bpy.ops.import_scene.obj(filepath=str(path))
    elif ext in {".glb", ".gltf"}:
        bpy.ops.import_scene.gltf(filepath=str(path))
    else:
        raise ValueError(f"Unsupported mesh format: {path}")

    # Find newly imported objects
    new_objects = [
        bpy.data.objects[name]
        for name in bpy.data.objects.keys()
        if name not in existing
    ]

    if not new_objects:
        raise RuntimeError(f"No objects imported from {path}")

    # Return the first mesh object (or first object if no meshes)
    for obj in new_objects:
        if obj.type == "MESH":
            return obj
    return new_objects[0]


def build_from_manifest(manifest_path: Path) -> bpy.types.Collection:
    """
    Load manifest and import all objects into a collection.

    Idempotent: clears existing objects in the collection before importing.
    """
    with manifest_path.open() as f:
        manifest = json.load(f)

    env_name = manifest["env_name"]

    # Get or create environment collection
    env_coll = bpy.data.collections.get(env_name)
    if env_coll is None:
        env_coll = bpy.data.collections.new(env_name)
        bpy.context.scene.collection.children.link(env_coll)

    # Idempotent: clear previous objects in this collection
    for obj in list(env_coll.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

    imported_count = 0
    skipped_count = 0

    # Import each object from manifest
    for obj_desc in manifest["objects"]:
        mesh_path = Path(obj_desc["mesh_path"])

        # Skip placeholder files (empty or just comments)
        if not mesh_path.exists():
            print(f"[WARN] Mesh not found, skipping: {mesh_path}")
            skipped_count += 1
            continue

        if mesh_path.stat().st_size < 100:
            print(f"[WARN] Mesh appears to be placeholder, skipping: {mesh_path}")
            skipped_count += 1
            continue

        try:
            obj = import_mesh(mesh_path)
        except Exception as e:
            print(f"[WARN] Failed to import {mesh_path}: {e}")
            skipped_count += 1
            continue

        # Move to environment collection
        for coll in obj.users_collection:
            coll.objects.unlink(obj)
        env_coll.objects.link(obj)

        # Apply transforms from manifest
        obj.location = obj_desc.get("location") or [0.0, 0.0, 0.0]
        obj.rotation_euler = obj_desc.get("rotation_euler") or [0.0, 0.0, 0.0]
        obj.scale = obj_desc.get("scale") or [1.0, 1.0, 1.0]

        print(f"[OK] Imported: {obj.name} from {mesh_path.name}")
        imported_count += 1

    print(f"\n[MANIFEST] Imported {imported_count} objects, skipped {skipped_count}")
    return env_coll


# For direct execution in Blender
if __name__ == "__main__":
    import sys

    # Determine root directory
    if bpy.data.filepath:
        script_dir = Path(bpy.data.filepath).parent
    else:
        script_dir = Path(__file__).parent

    root = script_dir.parent

    # Accept manifest path as argument or use default
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        manifest_path = Path(sys.argv[1])
    else:
        manifest_path = root / "manifests" / "battlestation_batman_manifest.json"

    if manifest_path.exists():
        build_from_manifest(manifest_path)
    else:
        print(f"Manifest not found: {manifest_path}")
        print("Available manifests:")
        manifest_dir = root / "manifests"
        if manifest_dir.exists():
            for f in manifest_dir.glob("*_manifest.json"):
                print(f"  - {f}")
