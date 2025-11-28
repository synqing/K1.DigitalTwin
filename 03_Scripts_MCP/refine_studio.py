"""
refine_studio.py
K1-Lightwave Digital Twin - Scene Refinement & Composition Fix

Performs:
1. Macro camera repositioning with updated DOF
2. Material imperfection pass (anodization grain)
3. Bounce card lighting
4. Void background setup
5. Render output
"""

import bpy
import math


# =============================================================================
# 1. THE "MACRO" CAMERA FIX
# =============================================================================

def fix_macro_camera():
    """Reposition Cam_Hero_1 for macro framing and update DOF."""
    cam_obj = bpy.data.objects.get('Cam_Hero_1')
    focus_target = bpy.data.objects.get('Focus_Target')

    if not cam_obj:
        print("ERROR: Cam_Hero_1 not found!")
        return False

    # Move camera closer - 3/4 angle at ~1m distance
    cam_obj.location = (0.8, -0.8, 0.6)

    # Update DOF settings
    cam_data = cam_obj.data
    cam_data.dof.use_dof = True
    cam_data.dof.aperture_fstop = 4.0

    if focus_target:
        cam_data.dof.focus_object = focus_target
        print(f"  Focus object: {focus_target.name}")
    else:
        print("  WARNING: Focus_Target not found, using distance-based focus")
        cam_data.dof.focus_distance = 1.0

    print(f"  Camera location: {tuple(round(v, 2) for v in cam_obj.location)}")
    print(f"  F-Stop: {cam_data.dof.aperture_fstop}")

    return True


# =============================================================================
# 2. MATERIAL UPGRADE (THE "IMPERFECTION PASS")
# =============================================================================

def add_micro_roughness(material_name):
    """
    Inject micro-roughness (anodization grain) into a material's node tree.
    Adds Noise Texture -> Color Ramp -> MixRGB to modulate roughness.
    """
    mat = bpy.data.materials.get(material_name)
    if not mat or not mat.use_nodes:
        print(f"  WARNING: Material '{material_name}' not found or not using nodes")
        return False

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Find the Principled BSDF
    principled = None
    for node in nodes:
        if node.type == 'BSDF_PRINCIPLED':
            principled = node
            break

    if not principled:
        print(f"  WARNING: No Principled BSDF found in '{material_name}'")
        return False

    # Get current roughness value
    current_roughness = principled.inputs['Roughness'].default_value

    # Check if roughness is already connected
    roughness_input = principled.inputs['Roughness']
    existing_link = None
    for link in roughness_input.links:
        existing_link = link
        break

    # Create Texture Coordinate node for proper mapping
    tex_coord = nodes.new('ShaderNodeTexCoord')
    tex_coord.location = (-900, -400)

    # Create Noise Texture for micro-roughness
    noise = nodes.new('ShaderNodeTexNoise')
    noise.location = (-700, -400)
    noise.inputs['Scale'].default_value = 800.0
    noise.inputs['Detail'].default_value = 16.0
    noise.inputs['Roughness'].default_value = 0.6

    # Create Color Ramp to constrict values (0.4 - 0.6 range)
    ramp = nodes.new('ShaderNodeValToRGB')
    ramp.location = (-500, -400)
    ramp.color_ramp.elements[0].position = 0.4
    ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ramp.color_ramp.elements[1].position = 0.6
    ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)

    # Create Value node to hold base roughness
    base_roughness = nodes.new('ShaderNodeValue')
    base_roughness.location = (-500, -250)
    base_roughness.outputs[0].default_value = current_roughness
    base_roughness.label = "Base Roughness"

    # Create MixRGB node set to Overlay with low factor
    mix = nodes.new('ShaderNodeMixRGB')
    mix.location = (-300, -400)
    mix.blend_type = 'OVERLAY'
    mix.inputs['Fac'].default_value = 0.1

    # Connect the nodes
    links.new(tex_coord.outputs['Object'], noise.inputs['Vector'])
    links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
    links.new(base_roughness.outputs[0], mix.inputs['Color1'])
    links.new(ramp.outputs['Color'], mix.inputs['Color2'])

    # Disconnect existing roughness link if any
    if existing_link:
        links.remove(existing_link)

    # Connect mix output to roughness
    links.new(mix.outputs['Color'], principled.inputs['Roughness'])

    print(f"  Added micro-roughness to '{material_name}' (base: {current_roughness:.2f})")
    return True


def upgrade_materials():
    """Apply imperfection pass to target materials."""
    targets = ['Mt_FoundersRed', 'Mt_Gunmetal']

    for mat_name in targets:
        add_micro_roughness(mat_name)


# =============================================================================
# 3. LIGHTING UPGRADE (THE "BOUNCE CARD")
# =============================================================================

def create_bounce_card():
    """Create a bounce card for soft fill lighting."""

    # Remove existing bounce card if present
    existing = bpy.data.objects.get('Light_Bounce_Card')
    if existing:
        bpy.data.objects.remove(existing, do_unlink=True)

    # Create plane
    bpy.ops.mesh.primitive_plane_add(size=0.5, location=(-1.0, -1.0, 0.5))
    bounce_card = bpy.context.active_object
    bounce_card.name = 'Light_Bounce_Card'

    # Rotate to aim at origin (K1 location)
    # Calculate direction to target
    target = (0.0, 0.0, 0.15)  # Slightly above origin where K1 sits
    dx = target[0] - bounce_card.location[0]
    dy = target[1] - bounce_card.location[1]
    dz = target[2] - bounce_card.location[2]

    # Calculate rotation angles
    yaw = math.atan2(dx, dy)
    dist_xy = math.sqrt(dx*dx + dy*dy)
    pitch = math.atan2(dz, dist_xy)

    # Plane default normal is +Z, so we need to rotate to face the target
    bounce_card.rotation_euler = (math.pi/2 + pitch, 0.0, yaw)

    # Create emission material
    mat_name = 'Mt_Emission_Soft'
    existing_mat = bpy.data.materials.get(mat_name)
    if existing_mat:
        bpy.data.materials.remove(existing_mat)

    mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Clear default nodes
    for node in list(nodes):
        nodes.remove(node)

    # Create Emission shader
    emission = nodes.new('ShaderNodeEmission')
    emission.location = (0, 0)
    emission.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)  # Pure white
    emission.inputs['Strength'].default_value = 5.0

    # Create Output
    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (200, 0)

    # Connect
    links.new(emission.outputs['Emission'], output.inputs['Surface'])

    # Apply material to bounce card
    bounce_card.data.materials.append(mat)

    # Set ray visibility - hide from camera but visible to reflections
    bounce_card.visible_camera = False
    bounce_card.visible_diffuse = True
    bounce_card.visible_glossy = True
    bounce_card.visible_transmission = True
    bounce_card.visible_volume_scatter = True
    bounce_card.visible_shadow = False

    print(f"  Created bounce card at {tuple(round(v, 2) for v in bounce_card.location)}")
    print(f"  Emission strength: 5.0, Camera visible: False")

    return bounce_card


# =============================================================================
# 4. THE "VOID" BACKGROUND
# =============================================================================

def hex_to_rgb(hex_str):
    """Convert hex color to RGB tuple (0-1 range)."""
    hex_str = hex_str.strip('#')
    return tuple(int(hex_str[i:i+2], 16) / 255.0 for i in (0, 2, 4))


def setup_void_background():
    """Set world background to dark charcoal void."""
    scene = bpy.context.scene
    world = scene.world

    if world is None:
        world = bpy.data.worlds.new('World')
        scene.world = world

    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links

    # Find or create Background node
    bg = None
    output = None
    for node in nodes:
        if node.type == 'BACKGROUND':
            bg = node
        elif node.type == 'OUTPUT_WORLD':
            output = node

    if not bg:
        bg = nodes.new('ShaderNodeBackground')
    if not output:
        output = nodes.new('ShaderNodeOutputWorld')

    # Set void color - Hex #0D0D0D (Dark Charcoal)
    void_color = hex_to_rgb('0D0D0D')
    bg.inputs['Color'].default_value = (*void_color, 1.0)
    bg.inputs['Strength'].default_value = 1.0

    # Ensure connection
    if not bg.outputs['Background'].is_linked:
        links.new(bg.outputs['Background'], output.inputs['Surface'])

    print(f"  World background: #0D0D0D (Dark Charcoal)")
    print(f"  Clean infinite void - no gradient")

    return True


# =============================================================================
# 5. RENDER CHECK
# =============================================================================

def setup_render_and_execute():
    """Configure output path and trigger render."""
    import os

    scene = bpy.context.scene

    # Set output format
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.compression = 15

    # Set output path
    scene.render.filepath = "//99_Render_Output/_drafts/K1_Macro_v02.png"

    # Ensure output directory exists
    out_dir = bpy.path.abspath("//99_Render_Output/_drafts")
    os.makedirs(out_dir, exist_ok=True)

    print(f"  Output path: {scene.render.filepath}")
    print(f"  Resolution: {scene.render.resolution_x}x{scene.render.resolution_y}")
    print(f"  Samples: {scene.cycles.samples}")

    # Execute render
    print("\n=== STARTING RENDER ===")
    bpy.ops.render.render(write_still=True)
    print("=== RENDER COMPLETE ===")

    # Verify output
    full_path = bpy.path.abspath(scene.render.filepath)
    if os.path.exists(full_path):
        size = os.path.getsize(full_path)
        print(f"  Output file: {full_path}")
        print(f"  File size: {size:,} bytes")
        return True
    else:
        print(f"  ERROR: Output file not found!")
        return False


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Execute all refinement steps."""
    print("=" * 60)
    print("K1-LIGHTWAVE STUDIO REFINEMENT")
    print("=" * 60)

    print("\n[1/5] MACRO CAMERA FIX")
    fix_macro_camera()

    print("\n[2/5] MATERIAL IMPERFECTION PASS")
    upgrade_materials()

    print("\n[3/5] BOUNCE CARD LIGHTING")
    create_bounce_card()

    print("\n[4/5] VOID BACKGROUND")
    setup_void_background()

    print("\n[5/5] RENDER OUTPUT")
    setup_render_and_execute()

    print("\n" + "=" * 60)
    print("REFINEMENT COMPLETE")
    print("=" * 60)


if __name__ == '__main__':
    main()
