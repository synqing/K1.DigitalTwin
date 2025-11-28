"""
build_battlestation_batman.py

Batman-style ultrawide battlestation environment.

Prerequisites:
- K1_MASTER_BUILD.py must have run (K1 exists in scene)
- battlestation_batman_manifest.json must exist

Run via BlenderMCP after K1_MASTER_BUILD.py.
"""

import sys
from pathlib import Path

import bpy

# Add scripts directory to path for imports
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_environment_from_manifest import build_from_manifest


def get_root() -> Path:
    """Return 04_SAM3D_Environments/ root directory."""
    return SCRIPT_DIR.parent


def get_k1_object() -> bpy.types.Object:
    """Find K1 object in scene. Must exist from K1_MASTER_BUILD.py."""
    candidates = ["K1", "K1_Lightwave", "K1.Body", "K1_Body", "K1_Chassis"]

    # Try exact matches first
    for name in candidates:
        obj = bpy.data.objects.get(name)
        if obj:
            return obj

    # Try partial match
    for obj in bpy.data.objects:
        if "k1" in obj.name.lower():
            return obj

    raise RuntimeError(
        "K1 object not found. Run K1_MASTER_BUILD.py first.\n"
        "Expected: K1_MASTER_BUILD.py in ../03_Scripts_MCP/"
    )


def ensure_idempotent():
    """Remove existing environment objects to ensure clean rebuild."""
    env_objects = [
        "Desk",
        "BackWall",
        "Floor",
        "DeskMesh",
        "CAM_battlestation_main",
        "KeyLight",
        "RimLight",
        "FillLight",
        "Mt_Desk_Dark",
        "Mt_Wall_Dark",
        "Mt_Floor_Dark",
    ]
    for name in env_objects:
        obj = bpy.data.objects.get(name)
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)

    # Also clean up materials
    for name in ["Mt_Desk_Dark", "Mt_Wall_Dark", "Mt_Floor_Dark"]:
        mat = bpy.data.materials.get(name)
        if mat:
            bpy.data.materials.remove(mat)


def create_basic_surfaces():
    """Create desk, wall, and floor planes."""

    # Desk surface (1.6m x 0.7m at 0.75m height)
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0.0, 0.0, 0.75))
    desk = bpy.context.active_object
    desk.name = "Desk"
    desk.scale = (0.8, 0.35, 1.0)  # 1.6m x 0.7m

    # Dark desk material
    mat = bpy.data.materials.new(name="Mt_Desk_Dark")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.02, 0.02, 0.02, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.4
    desk.data.materials.append(mat)

    # Back wall (3m x 2m)
    bpy.ops.mesh.primitive_plane_add(size=3.0, location=(0.0, -0.4, 1.6))
    wall = bpy.context.active_object
    wall.name = "BackWall"
    wall.rotation_euler[0] = 1.5708  # 90 degrees to face camera

    # Dark wall material
    mat = bpy.data.materials.new(name="Mt_Wall_Dark")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.01, 0.01, 0.01, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.9
    wall.data.materials.append(mat)

    # Floor (4m x 4m)
    bpy.ops.mesh.primitive_plane_add(size=4.0, location=(0.0, 0.0, 0.0))
    floor = bpy.context.active_object
    floor.name = "Floor"

    # Dark floor material
    mat = bpy.data.materials.new(name="Mt_Floor_Dark")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.015, 0.015, 0.015, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.7
    floor.data.materials.append(mat)


def place_k1():
    """Position K1 as hero object on desk."""
    k1 = get_k1_object()
    k1.location = (0.0, 0.15, 0.78)  # Center of desk, slightly forward
    k1.rotation_euler = (0.0, 0.0, 0.0)
    print(f"[OK] K1 positioned: {k1.name} at {tuple(k1.location)}")


def setup_camera():
    """Create main camera with DOF focused on K1."""
    cam_name = "CAM_battlestation_main"

    # Create camera
    cam_data = bpy.data.cameras.new(cam_name)
    cam = bpy.data.objects.new(cam_name, cam_data)
    bpy.context.scene.collection.objects.link(cam)

    # Position: front-facing, slightly elevated
    cam.location = (0.0, -1.8, 1.1)
    cam.rotation_euler = (1.2, 0.0, 0.0)  # ~69 degrees down

    # Lens settings
    cam.data.lens = 35.0
    cam.data.sensor_width = 36.0

    # Depth of field
    cam.data.dof.use_dof = True
    cam.data.dof.focus_object = get_k1_object()
    cam.data.dof.aperture_fstop = 4.0

    # Set as active camera
    bpy.context.scene.camera = cam
    print(f"[OK] Camera created: {cam_name}")


def setup_lights():
    """Create 3-point lighting rig for battlestation mood."""

    # Clear existing environment lights (preserve K1 studio lights if any)
    env_lights = ["KeyLight", "RimLight", "FillLight"]
    for name in env_lights:
        obj = bpy.data.objects.get(name)
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)

    # Key light - simulates monitor glow (cool blue-white)
    key_data = bpy.data.lights.new("KeyLight", type="AREA")
    key = bpy.data.objects.new("KeyLight", key_data)
    bpy.context.scene.collection.objects.link(key)
    key.location = (0.0, -0.3, 1.3)
    key.rotation_euler = (1.4, 0.0, 0.0)
    key_data.energy = 1500.0
    key_data.size = 1.2
    key_data.color = (0.9, 0.95, 1.0)  # Slight cool tint

    # Rim light - edge separation (warm accent)
    rim_data = bpy.data.lights.new("RimLight", type="AREA")
    rim = bpy.data.objects.new("RimLight", rim_data)
    bpy.context.scene.collection.objects.link(rim)
    rim.location = (-1.0, 0.2, 1.2)
    rim.rotation_euler = (1.3, 0.0, 0.6)
    rim_data.energy = 1000.0
    rim_data.size = 0.8
    rim_data.color = (1.0, 0.85, 0.7)  # Warm accent

    # Fill light - subtle ambient (neutral)
    fill_data = bpy.data.lights.new("FillLight", type="AREA")
    fill = bpy.data.objects.new("FillLight", fill_data)
    bpy.context.scene.collection.objects.link(fill)
    fill.location = (1.2, -1.2, 1.4)
    fill.rotation_euler = (1.2, 0.0, -0.5)
    fill_data.energy = 300.0
    fill_data.size = 1.5

    print("[OK] Lighting rig created: KeyLight, RimLight, FillLight")


def main():
    """Build complete battlestation_batman environment."""
    root = get_root()
    manifest = root / "manifests" / "battlestation_batman_manifest.json"

    print("\n" + "=" * 60)
    print("BUILD: battlestation_batman")
    print("=" * 60 + "\n")

    # Idempotent cleanup
    ensure_idempotent()

    # Import SAM3D meshes (if available)
    if manifest.exists():
        print("[1/5] Loading manifest meshes...")
        build_from_manifest(manifest)
    else:
        print(f"[1/5] SKIP: Manifest not found: {manifest}")

    # Create environment surfaces
    print("[2/5] Creating surfaces...")
    create_basic_surfaces()

    # Position K1
    print("[3/5] Positioning K1...")
    place_k1()

    # Camera setup
    print("[4/5] Setting up camera...")
    setup_camera()

    # Lighting
    print("[5/5] Creating lighting rig...")
    setup_lights()

    print("\n" + "=" * 60)
    print("BUILD COMPLETE: battlestation_batman")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
