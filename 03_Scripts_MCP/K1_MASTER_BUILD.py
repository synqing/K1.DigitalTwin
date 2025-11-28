"""
K1_MASTER_BUILD.py
K1-Lightwave Digital Twin - Master Scene Build (Single Source of Truth)

Complete pipeline in one pass:
1. System Reset (Cycles, AgX, Clean Slate)
2. Corrected Material Palette (Anthracite, Yellow, Rose Copper, Satin Silver, Silver Ghost)
3. Smart Material Assignment (by keyword)
4. Cinematic Studio Lighting (High Power)
5. Macro Camera Setup

All previous patch scripts are obsoleted by this single build.
"""

import bpy
import math
import os


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def hex_to_rgb(hex_str):
    """Convert hex color to RGB tuple (0-1 range)."""
    hex_str = hex_str.strip('#')
    return tuple(int(hex_str[i:i+2], 16) / 255.0 for i in (0, 2, 4))


def safe_set_input(bsdf, input_name, value):
    """Safely set BSDF input, handling missing inputs gracefully."""
    try:
        bsdf.inputs[input_name].default_value = value
    except (KeyError, AttributeError):
        pass  # Input doesn't exist in this Blender version


# =============================================================================
# PART 1: SYSTEM RESET
# =============================================================================

def reset_render_settings():
    """Reset render engine, samples, and color management."""
    scene = bpy.context.scene

    # Switch to Cycles
    scene.render.engine = 'CYCLES'
    cycles = scene.cycles
    cycles.feature_set = 'SUPPORTED'

    # GPU acceleration
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        if hasattr(prefs, 'get_devices'):
            prefs.compute_device_type = 'METAL'
        scene.cycles.device = 'GPU'
    except Exception:
        scene.cycles.device = 'CPU'

    # Sampling
    cycles.samples = 1024
    cycles.preview_samples = 128
    cycles.max_bounces = 12

    # Color Management
    try:
        scene.view_settings.view_transform = 'AgX'
    except Exception:
        pass
    scene.view_settings.look = 'AgX - High Contrast'

    # Resolution
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100

    print("✓ Render Settings: Cycles, 1024 samples, AgX High Contrast")


def reset_world_background():
    """Set world background to dark charcoal void."""
    scene = bpy.context.scene
    world = scene.world

    if world is None:
        world = bpy.data.worlds.new('World')
        scene.world = world

    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links

    # Clear default nodes
    for node in list(nodes):
        nodes.remove(node)

    # Create Background and Output
    bg = nodes.new('ShaderNodeBackground')
    output = nodes.new('ShaderNodeOutputWorld')

    # Set charcoal color
    void_color = hex_to_rgb('#0D0D0D')
    bg.inputs['Color'].default_value = (*void_color, 1.0)
    bg.inputs['Strength'].default_value = 1.0

    # Connect
    links.new(bg.outputs['Background'], output.inputs['Surface'])

    print("✓ World Background: #0D0D0D (Dark Charcoal Void)")


def cleanup_lights():
    """Delete all existing lights."""
    objs = [o for o in bpy.context.scene.objects if o.type == 'LIGHT']
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
    print(f"✓ Cleanup: Removed {len(objs)} existing lights")


def cleanup_materials():
    """Delete all existing materials to prevent ghost data."""
    count = 0
    for mat in list(bpy.data.materials):
        if mat.users == 0:  # Only delete unused materials
            bpy.data.materials.remove(mat)
            count += 1
    print(f"✓ Cleanup: Removed {count} unused materials")


# =============================================================================
# PART 2: CORRECTED MATERIAL PALETTE
# =============================================================================

def create_anthracite_body():
    """Mt_Body_Anthracite: Metallic with fine powder-coat grain."""
    # Create/reset material
    mat = bpy.data.materials.get('Mt_Body_Anthracite')
    if mat:
        bpy.data.materials.remove(mat)

    mat = bpy.data.materials.new(name='Mt_Body_Anthracite')
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Clear all nodes
    nodes.clear()

    # Create Principled BSDF
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (200, 0)
    bsdf.inputs['Base Color'].default_value = (*hex_to_rgb('#2F3133'), 1.0)
    bsdf.inputs['Metallic'].default_value = 1.0
    bsdf.inputs['Roughness'].default_value = 0.5

    # Micro-detail: Noise Texture for powder-coat grain
    tex_coord = nodes.new('ShaderNodeTexCoord')
    tex_coord.location = (-800, 0)

    noise = nodes.new('ShaderNodeTexNoise')
    noise.location = (-600, 0)
    noise.inputs['Scale'].default_value = 2000.0  # High scale = fine grain
    noise.inputs['Detail'].default_value = 16.0
    noise.inputs['Roughness'].default_value = 0.6

    bump = nodes.new('ShaderNodeBump')
    bump.location = (-400, 0)
    bump.inputs['Strength'].default_value = 0.02  # Subtle bump
    bump.inputs['Distance'].default_value = 0.005

    # Output
    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (400, 0)

    # Connect
    links.new(tex_coord.outputs['Object'], noise.inputs['Vector'])
    links.new(noise.outputs['Fac'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    print("✓ Mt_Body_Anthracite: #2F3133, Metallic 1.0, Noise Scale 2000 (fine grain)")
    return mat


def create_yellow_accents():
    """Mt_Accent_Yellow: Matte plastic, safety yellow."""
    mat = bpy.data.materials.get('Mt_Accent_Yellow')
    if mat:
        bpy.data.materials.remove(mat)

    mat = bpy.data.materials.new(name='Mt_Accent_Yellow')
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    nodes.clear()

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    bsdf.inputs['Base Color'].default_value = (*hex_to_rgb('#FFC400'), 1.0)
    safe_set_input(bsdf, 'Metallic', 0.0)  # Plastic
    safe_set_input(bsdf, 'Roughness', 0.4)

    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (300, 0)
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    print("✓ Mt_Accent_Yellow: #FFC400, Metallic 0.0, Roughness 0.4")
    return mat


def create_rose_copper_logo():
    """Mt_Logo_Copper: Rose/Red Copper (not brass/gold)."""
    mat = bpy.data.materials.get('Mt_Logo_Copper')
    if mat:
        bpy.data.materials.remove(mat)

    mat = bpy.data.materials.new(name='Mt_Logo_Copper')
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    nodes.clear()

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    bsdf.inputs['Base Color'].default_value = (*hex_to_rgb('#D67658'), 1.0)
    safe_set_input(bsdf, 'Metallic', 1.0)  # Full metal
    safe_set_input(bsdf, 'Roughness', 0.2)  # Polished

    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (300, 0)
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    print("✓ Mt_Logo_Copper: #D67658 (Rose Copper), Metallic 1.0, Roughness 0.2")
    return mat


def create_satin_silver_connector():
    """Mt_Satin_Silver: Brushed aluminum with anisotropic grain."""
    mat = bpy.data.materials.get('Mt_Satin_Silver')
    if mat:
        bpy.data.materials.remove(mat)

    mat = bpy.data.materials.new(name='Mt_Satin_Silver')
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    nodes.clear()

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    bsdf.inputs['Base Color'].default_value = (*hex_to_rgb('#E0E0E0'), 1.0)
    safe_set_input(bsdf, 'Metallic', 1.0)
    safe_set_input(bsdf, 'Roughness', 0.35)
    safe_set_input(bsdf, 'Anisotropic', 0.7)  # Brushed grain
    safe_set_input(bsdf, 'Anisotropic Rotation', 0.0)

    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (300, 0)
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    print("✓ Mt_Satin_Silver: #E0E0E0, Anisotropic 0.7 (brushed)")
    return mat


def create_silverghost_lgp():
    """Mt_SilverGhost: Frosted glass/metal for light guides."""
    mat = bpy.data.materials.get('Mt_SilverGhost')
    if mat:
        bpy.data.materials.remove(mat)

    mat = bpy.data.materials.new(name='Mt_SilverGhost')
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    nodes.clear()

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    bsdf.inputs['Base Color'].default_value = (*hex_to_rgb('#C8C8C8'), 1.0)
    safe_set_input(bsdf, 'Transmission', 0.95)
    safe_set_input(bsdf, 'Metallic', 0.3)
    safe_set_input(bsdf, 'Roughness', 0.3)
    safe_set_input(bsdf, 'IOR', 1.52)
    safe_set_input(bsdf, 'Alpha', 1.0)

    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (300, 0)
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    print("✓ Mt_SilverGhost: #C8C8C8, Trans 0.95 (frosted glass)")
    return mat


# =============================================================================
# PART 3: SMART MATERIAL ASSIGNMENT
# =============================================================================

def assign_materials_by_keyword():
    """Assign materials to objects based on name keywords."""
    materials = {
        'Mt_Body_Anthracite': ['body', 'chassis', 'main'],
        'Mt_Accent_Yellow': ['leg', 'stand', 'end', 'yellow'],
        'Mt_Logo_Copper': ['logo', 'text', 'badge'],
        'Mt_Satin_Silver': ['connect', 'bridge', 'middle'],
        'Mt_SilverGhost': ['guide', 'plate', 'lgp']
    }

    assigned = {name: 0 for name in materials}

    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue

        name_lower = obj.name.lower()

        for mat_name, keywords in materials.items():
            if any(k in name_lower for k in keywords):
                mat = bpy.data.materials.get(mat_name)
                if mat:
                    if len(obj.data.materials) > 0:
                        obj.data.materials[0] = mat
                    else:
                        obj.data.materials.append(mat)
                    assigned[mat_name] += 1
                break

    for mat_name, count in assigned.items():
        if count > 0:
            print(f"  {mat_name}: {count} object(s)")

    return assigned


# =============================================================================
# PART 4: CINEMATIC STUDIO LIGHTING
# =============================================================================

def look_at(obj, target=(0.0, 0.0, 0.0)):
    """Point object at target location."""
    dx = target[0] - obj.location[0]
    dy = target[1] - obj.location[1]
    dz = target[2] - obj.location[2]
    yaw = math.atan2(dx, dy)
    dist = math.sqrt(dx*dx + dy*dy)
    pitch = math.atan2(-dz, dist)
    obj.rotation_euler = (pitch, 0.0, yaw)


def create_area_light(name, shape, size_x, size_y, energy, color, location):
    """Create and position an area light."""
    light_data = bpy.data.lights.new(name=name, type='AREA')
    light_data.shape = shape

    if shape == 'RECTANGLE':
        light_data.size = size_x
        light_data.size_y = size_y
    else:
        light_data.size = size_x

    light_data.energy = energy
    light_data.color = color

    light_obj = bpy.data.objects.new(name, light_data)
    bpy.context.collection.objects.link(light_obj)
    light_obj.location = location
    look_at(light_obj)

    return light_obj


def setup_cinematic_lighting():
    """Create high-power studio lighting rig."""
    print("\n[CINEMATIC LIGHTING]")

    # Key (Softbox): Warm, directional
    key = create_area_light(
        'Key_Softbox', 'RECTANGLE',
        2.0, 2.0,  # 2m x 2m
        1500.0,    # 1500W
        hex_to_rgb('#FFF0EB'),  # Warm white
        (-3.0, 3.0, 3.0)
    )
    print("  ✓ Key_Softbox: 1500W, #FFF0EB (warm)")

    # Rim (Hero): High power backlight
    rim = create_area_light(
        'Rim_Hero', 'RECTANGLE',
        0.5, 2.0,  # 0.5m x 2m
        3000.0,    # 3000W
        (1.0, 1.0, 1.0),  # Pure white
        (0.0, -3.0, 3.0)
    )
    print("  ✓ Rim_Hero: 3000W, #FFFFFF (punch)")

    # Fill (Disk): Soft fill from above
    fill = create_area_light(
        'Fill_Disk', 'DISK',
        3.0, 3.0,  # 3m radius
        300.0,     # 300W
        hex_to_rgb('#E0E0FF'),  # Cool blue
        (3.0, 0.0, 2.0)
    )
    print("  ✓ Fill_Disk: 300W, #E0E0FF (cool)")


# =============================================================================
# PART 5: MACRO CAMERA SETUP
# =============================================================================

def setup_macro_camera():
    """Create and position Cam_Hero_1 for macro close-up."""
    print("\n[MACRO CAMERA]")

    # Delete existing camera if present
    existing_cam = bpy.data.objects.get('Cam_Hero_1')
    if existing_cam:
        bpy.data.objects.remove(existing_cam, do_unlink=True)

    existing_focus = bpy.data.objects.get('Focus_Target')
    if existing_focus:
        bpy.data.objects.remove(existing_focus, do_unlink=True)

    # Create Focus Target (empty)
    focus_target = bpy.data.objects.new('Focus_Target', None)
    focus_target.location = (0.0, 0.0, 0.0)
    bpy.context.collection.objects.link(focus_target)

    # Create Camera
    cam_data = bpy.data.cameras.new(name='Cam_Hero_1')
    cam_obj = bpy.data.objects.new('Cam_Hero_1', cam_data)
    bpy.context.collection.objects.link(cam_obj)

    # Camera position
    cam_obj.location = (0.8, -0.8, 0.6)
    cam_data.lens = 85.0

    # Add Track-To constraint
    track_constraint = cam_obj.constraints.new(type='TRACK_TO')
    track_constraint.target = focus_target
    track_constraint.track_axis = 'TRACK_NEGATIVE_Z'
    track_constraint.up_axis = 'UP_Y'

    # DOF Setup
    cam_data.dof.use_dof = True
    cam_data.dof.focus_object = focus_target
    cam_data.dof.aperture_fstop = 16.0

    # Set as active camera
    bpy.context.scene.camera = cam_obj

    print("  ✓ Cam_Hero_1: (0.8, -0.8, 0.6), 85mm, f/16")


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Execute complete K1-Lightwave scene build."""
    print("=" * 70)
    print("K1-LIGHTWAVE MASTER BUILD (SINGLE SOURCE OF TRUTH)")
    print("=" * 70)

    print("\n[PART 1: SYSTEM RESET]")
    cleanup_materials()
    cleanup_lights()
    reset_render_settings()
    reset_world_background()

    print("\n[PART 2: MATERIAL PALETTE (CORRECTED)]")
    create_anthracite_body()
    create_yellow_accents()
    create_rose_copper_logo()
    create_satin_silver_connector()
    create_silverghost_lgp()

    print("\n[PART 3: MATERIAL ASSIGNMENT]")
    assigned = assign_materials_by_keyword()

    setup_cinematic_lighting()
    setup_macro_camera()

    print("\n" + "=" * 70)
    print("✓ K1-LIGHTWAVE SCENE READY FOR RENDER")
    print("=" * 70)
    print("\nPalette:")
    print("  • Anthracite Body (Powder-Coat, Fine Grain)")
    print("  • Yellow Accents (Matte Plastic)")
    print("  • Rose Copper Logo (Polished Metal)")
    print("  • Satin Silver Connector (Brushed Aluminum)")
    print("  • Silver Ghost LGP (Frosted Glass)")
    print("\n" + "=" * 70)


if __name__ == '__main__':
    main()
