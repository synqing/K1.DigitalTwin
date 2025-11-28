"""
build_hackers_workbench.py
K1-Lightwave Digital Twin - "Hacker's Workbench" Vignette

Creates a focused, story-driven scene around the K1:
- Self-healing cutting mat with procedural grid (context & scale)
- Scattered mechanical switches & keyboard placeholder
- Moody, precise lighting
- Camera positioned for bokeh (background/foreground blur)

NOT a full room—a vignette that fades to void.
"""

import bpy
import math
import random


def hex_to_rgb(hex_str):
    """Convert hex color to RGB tuple (0-1 range)."""
    hex_str = hex_str.strip('#')
    return tuple(int(hex_str[i:i+2], 16) / 255.0 for i in (0, 2, 4))


def safe_set_input(bsdf, input_name, value):
    """Safely set BSDF input, handling missing inputs gracefully."""
    try:
        bsdf.inputs[input_name].default_value = value
    except (KeyError, AttributeError):
        pass


# =============================================================================
# 1. CUTTING MAT (GROUND PLANE WITH GRID)
# =============================================================================

def create_cutting_mat():
    """Create self-healing cutting mat with procedural grid texture."""
    print("\n[1] CUTTING MAT WITH GRID")

    # Delete existing generic desk
    for obj_name in ['Desk_Surface', 'Monitor_Stand', 'Monitor_Screen',
                      'Keyboard', 'Mouse_Pad', 'Light_Window', 'Light_Desk_Lamp',
                      'Light_Ambient', 'Cam_Environment']:
        obj = bpy.data.objects.get(obj_name)
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)

    # Create cutting mat plane
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0.0, 0.0, -0.501))
    mat_obj = bpy.context.active_object
    mat_obj.name = 'Env_CuttingMat'
    mat_obj.scale = (4.0, 2.0, 1.0)  # 4m x 2m

    # Create material with procedural grid
    mat = bpy.data.materials.new(name='Mt_CuttingMat')
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # Base BSDF
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (400, 0)
    bsdf.inputs['Base Color'].default_value = (*hex_to_rgb('#1A1A1A'), 1.0)
    safe_set_input(bsdf, 'Metallic', 0.0)
    safe_set_input(bsdf, 'Roughness', 0.8)  # Matte, non-slip

    # Texture Coordinate
    tex_coord = nodes.new('ShaderNodeTexCoord')
    tex_coord.location = (-800, 0)

    # Brick Texture for grid pattern
    brick = nodes.new('ShaderNodeTexBrick')
    brick.location = (-600, 0)
    brick.inputs['Scale'].default_value = 20.0  # 20 units = ~1cm grid
    brick.inputs['Mortar Size'].default_value = 0.02
    brick.inputs['Bias'].default_value = 0.95  # Mostly dark, thin white lines

    # ColorRamp to control line visibility
    ramp = nodes.new('ShaderNodeValToRGB')
    ramp.location = (-400, 0)
    # Dark at 0, white at 1
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (26/255.0, 26/255.0, 26/255.0, 1.0)
    ramp.color_ramp.elements[1].position = 1.0
    ramp.color_ramp.elements[1].color = (204/255.0, 204/255.0, 204/255.0, 1.0)

    # Mix into base color
    mix = nodes.new('ShaderNodeMix')
    mix.location = (0, 0)
    mix.data_type = 'RGBA'
    mix.inputs['Factor'].default_value = 0.05  # 5% grid visibility

    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (600, 0)

    # Connect
    links.new(tex_coord.outputs['Object'], brick.inputs['Vector'])
    links.new(brick.outputs['Color'], ramp.inputs['Fac'])
    links.new(ramp.outputs['Color'], mix.inputs['A'])
    links.new(bsdf.outputs['BSDF'], mix.inputs['B'])
    links.new(mix.outputs['Result'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    mat_obj.data.materials.append(mat)
    print("  ✓ Cutting mat: Dark grey with white grid lines (4m × 2m)")
    print("  ✓ Material: Matte rubber (Roughness 0.8)")


# =============================================================================
# 2. PROP: MECHANICAL KEYBOARD PLACEHOLDER
# =============================================================================

def create_keyboard_prop():
    """Create 65% keyboard placeholder."""
    print("\n[2] KEYBOARD PROP")

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(-0.4, 0.3, 0.015))
    kb = bpy.context.active_object
    kb.name = 'Prop_Keyboard'
    kb.scale = (0.32, 0.12, 0.03)  # 65% layout proportions
    kb.rotation_euler = (0, 0, math.radians(8))  # Casual angle

    # Use existing Anthracite material
    mat = bpy.data.materials.get('Mt_Body_Anthracite')
    if mat:
        kb.data.materials.append(mat)

    print("  ✓ Keyboard: 65% form factor, Anthracite color, 8° rotation")


# =============================================================================
# 3. PROPS: SCATTERED MECHANICAL SWITCHES
# =============================================================================

def create_switch_props():
    """Create 3-4 scattered switch placeholders."""
    print("\n[3] MECHANICAL SWITCHES")

    switch_positions = [
        (0.25, -0.35, 0.008),
        (0.45, -0.25, 0.008),
        (-0.15, -0.4, 0.008),
        (0.05, -0.5, 0.008),
    ]

    mat_yellow = bpy.data.materials.get('Mt_Accent_Yellow')
    mat_copper = bpy.data.materials.get('Mt_Logo_Copper')

    for i, pos in enumerate(switch_positions):
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=pos)
        switch = bpy.context.active_object
        switch.name = f'Prop_Switch_{i+1:02d}'
        switch.scale = (0.016, 0.016, 0.012)  # Cherry MX proportions

        # Random rotation for natural look
        switch.rotation_euler = (
            math.radians(random.uniform(-10, 10)),
            math.radians(random.uniform(-10, 10)),
            math.radians(random.uniform(0, 360))
        )

        # Alternate colors (yellow housing, copper contacts)
        if i % 2 == 0:
            if mat_yellow:
                switch.data.materials.append(mat_yellow)
        else:
            if mat_copper:
                switch.data.materials.append(mat_copper)

    print(f"  ✓ Switches: 4 scattered props (randomly rotated)")


# =============================================================================
# 4. CAMERA ADJUSTMENT (LOOKING DOWN AT WORKBENCH)
# =============================================================================

def adjust_camera():
    """Reposition camera for downward "looking at workbench" angle."""
    print("\n[4] CAMERA ADJUSTMENT")

    cam = bpy.data.objects.get('Cam_Hero_1')
    if cam:
        # Higher angle, looking down slightly
        cam.location = (0.3, -1.2, 0.8)

        # Point at K1
        target = (0.0, 0.2, 0.15)
        dx = target[0] - cam.location[0]
        dy = target[1] - cam.location[1]
        dz = target[2] - cam.location[2]
        yaw = math.atan2(dx, dy)
        dist = math.sqrt(dx*dx + dy*dy)
        pitch = math.atan2(-dz, dist)
        cam.rotation_euler = (pitch, 0.0, yaw)

        # Increase DOF depth blur for bokeh effect
        cam.data.dof.aperture_fstop = 4.0  # Shallower DOF
        cam.data.dof.focus_distance = 1.2

        print("  ✓ Camera: Higher angle, f/4 (bokeh on keyboard/switches)")
        print("  ✓ Focus locked on K1")


# =============================================================================
# 5. LIGHTING ADJUSTMENT
# =============================================================================

def adjust_lighting():
    """Tweak lights for workbench mood."""
    print("\n[5] LIGHTING ADJUSTMENT")

    # Key light - move slightly to create shadows across mat
    key = bpy.data.objects.get('Key_Softbox')
    if key:
        key.location = (-2.0, 1.0, 2.0)
        print("  ✓ Key light: Repositioned for mat shadows")

    # Rim light - ensure strong separation
    rim = bpy.data.objects.get('Rim_Hero')
    if rim:
        rim.data.energy = 3000.0
        print("  ✓ Rim light: 3000W for K1 separation")

    # Fill light - soft from above
    fill = bpy.data.objects.get('Fill_Disk')
    if fill:
        fill.location = (0.5, 0.5, 2.5)
        fill.data.energy = 200.0
        print("  ✓ Fill light: Soft overhead")


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Build the Hacker's Workbench vignette."""
    print("\n" + "="*70)
    print("BUILDING: HACKER'S WORKBENCH VIGNETTE")
    print("="*70)

    create_cutting_mat()
    create_keyboard_prop()
    create_switch_props()
    adjust_camera()
    adjust_lighting()

    print("\n" + "="*70)
    print("✓ WORKBENCH COMPLETE")
    print("="*70)
    print("\nScene Context:")
    print("  • Cutting Mat: Scale reference & precision context")
    print("  • Props: Tells the 'builder' story")
    print("  • Lighting: Moody, focused on K1")
    print("  • Camera: f/4 bokeh, looking down at workspace")
    print("\nReady to render hero shots showing K1 in its natural habitat.")


if __name__ == '__main__':
    main()
