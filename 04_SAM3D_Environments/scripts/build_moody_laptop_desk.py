"""
build_moody_laptop_desk.py

Dark, minimal desk scene lit by a single warm lamp.

Prerequisites:
- K1_MASTER_BUILD.py must have run (K1 exists in scene)
- moody_laptop_manifest.json must exist

Run via BlenderMCP after K1_MASTER_BUILD.py.
"""

import sys
from pathlib import Path

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_environment_from_manifest import build_from_manifest


def get_root() -> Path:
    return SCRIPT_DIR.parent


def get_k1_object() -> bpy.types.Object:
    candidates = ["K1", "K1_Lightwave", "K1.Body", "K1_Body", "K1_Chassis"]
    for name in candidates:
        obj = bpy.data.objects.get(name)
        if obj:
            return obj
    for obj in bpy.data.objects:
        if "k1" in obj.name.lower():
            return obj
    raise RuntimeError("K1 object not found. Run K1_MASTER_BUILD.py first.")


def ensure_idempotent():
    env_objects = [
        "Desk",
        "BackWall",
        "Floor",
        "CAM_moody_main",
        "KeyLamp",
        "Fill",
    ]
    for name in env_objects:
        obj = bpy.data.objects.get(name)
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)

    # Clean up materials
    for name in ["Mt_Desk_Wood", "Mt_Curtain_Dark", "Mt_Floor_Shadow"]:
        mat = bpy.data.materials.get(name)
        if mat:
            bpy.data.materials.remove(mat)


def create_surfaces():
    """Create minimal desk and background."""

    # Desk surface (1.8m x 0.8m at 0.75m)
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0.0, 0.0, 0.75))
    desk = bpy.context.active_object
    desk.name = "Desk"
    desk.scale = (0.9, 0.4, 1.0)

    # Warm wood-tone desk
    mat = bpy.data.materials.new(name="Mt_Desk_Wood")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.08, 0.04, 0.02, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.6
    desk.data.materials.append(mat)

    # Back wall / curtain (dark, absorbs light)
    bpy.ops.mesh.primitive_plane_add(size=3.0, location=(0.0, -0.6, 1.6))
    wall = bpy.context.active_object
    wall.name = "BackWall"
    wall.rotation_euler[0] = 1.5708

    mat = bpy.data.materials.new(name="Mt_Curtain_Dark")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.005, 0.005, 0.008, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.95
    wall.data.materials.append(mat)

    # Floor (barely visible in shadows)
    bpy.ops.mesh.primitive_plane_add(size=4.0, location=(0.0, 0.0, 0.0))
    floor = bpy.context.active_object
    floor.name = "Floor"

    mat = bpy.data.materials.new(name="Mt_Floor_Shadow")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.01, 0.01, 0.01, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.8
    floor.data.materials.append(mat)


def place_k1():
    k1 = get_k1_object()
    k1.location = (0.12, 0.0, 0.78)  # Slightly off-center for composition
    k1.rotation_euler = (0.0, 0.0, -0.1)  # Subtle angle
    print(f"[OK] K1 positioned: {k1.name}")


def setup_camera():
    cam_data = bpy.data.cameras.new("CAM_moody_main")
    cam = bpy.data.objects.new("CAM_moody_main", cam_data)
    bpy.context.scene.collection.objects.link(cam)

    cam.location = (0.0, -1.3, 0.95)
    cam.rotation_euler = (1.15, 0.0, 0.0)
    cam.data.lens = 50.0  # Tighter framing
    cam.data.dof.use_dof = True
    cam.data.dof.focus_object = get_k1_object()
    cam.data.dof.aperture_fstop = 2.8  # Shallow DOF for intimacy
    bpy.context.scene.camera = cam
    print("[OK] Camera created: CAM_moody_main")


def setup_lights():
    """Single warm key + subtle cool fill for moody atmosphere."""

    env_lights = ["KeyLamp", "Fill"]
    for name in env_lights:
        obj = bpy.data.objects.get(name)
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)

    # Warm key - simulates desk lamp (point light for sharp shadows)
    key_data = bpy.data.lights.new("KeyLamp", type="POINT")
    key = bpy.data.objects.new("KeyLamp", key_data)
    bpy.context.scene.collection.objects.link(key)
    key.location = (-0.3, -0.15, 1.1)
    key_data.energy = 600.0
    key_data.color = (1.0, 0.7, 0.4)  # Warm incandescent
    key_data.shadow_soft_size = 0.05  # Sharp shadows

    # Cool fill - barely visible ambient (screen reflection simulation)
    fill_data = bpy.data.lights.new("Fill", type="AREA")
    fill = bpy.data.objects.new("Fill", fill_data)
    bpy.context.scene.collection.objects.link(fill)
    fill.location = (0.8, -1.2, 1.3)
    fill.rotation_euler = (1.1, 0.0, -0.4)
    fill_data.energy = 80.0  # Very subtle
    fill_data.color = (0.6, 0.7, 1.0)  # Cool contrast
    fill_data.size = 1.0

    print("[OK] Lighting created: KeyLamp (warm), Fill (cool)")


def main():
    root = get_root()
    manifest = root / "manifests" / "moody_laptop_manifest.json"

    print("\n" + "=" * 60)
    print("BUILD: moody_laptop_desk")
    print("=" * 60 + "\n")

    ensure_idempotent()

    if manifest.exists():
        print("[1/5] Loading manifest meshes...")
        build_from_manifest(manifest)
    else:
        print(f"[1/5] SKIP: Manifest not found: {manifest}")

    print("[2/5] Creating surfaces...")
    create_surfaces()

    print("[3/5] Positioning K1...")
    place_k1()

    print("[4/5] Setting up camera...")
    setup_camera()

    print("[5/5] Creating lighting rig...")
    setup_lights()

    print("\n" + "=" * 60)
    print("BUILD COMPLETE: moody_laptop_desk")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
