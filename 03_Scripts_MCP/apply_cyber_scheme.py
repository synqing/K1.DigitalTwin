"""
apply_cyber_scheme.py
K1-Lightwave Digital Twin - Spectra-Industrial Anthracite Variant

Replaces current material palette with Anthracite/Yellow/Copper scheme:
- Body: Metallic Anthracite (#2F3133)
- Accents: Safety Yellow (#FFC400)
- Logo: Metallic Copper (#B87333)
"""

import bpy


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


def find_material_by_name(search_terms):
    """
    Find a material by searching for any of the given terms in its name.
    Returns the first matching material or None.
    """
    for mat in bpy.data.materials:
        mat_name_lower = mat.name.lower()
        for term in search_terms:
            if term.lower() in mat_name_lower:
                return mat
    return None


def ensure_bsdf_node(mat):
    """
    Ensure material has a Principled BSDF node.
    Returns the BSDF node (creates one if necessary).
    """
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Find existing Principled BSDF
    for node in nodes:
        if node.type == 'BSDF_PRINCIPLED':
            return node

    # Create new BSDF if none exists
    for n in list(nodes):
        if n.type != 'OUTPUT_MATERIAL':
            nodes.remove(n)

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)

    # Ensure output exists and is connected
    output = None
    for n in nodes:
        if n.type == 'OUTPUT_MATERIAL':
            output = n
            break

    if output is None:
        output = nodes.new('ShaderNodeOutputMaterial')

    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    return bsdf


def update_body_material():
    """Update body material to Metallic Anthracite."""
    # Find existing body material
    mat = find_material_by_name(['FoundersRed', 'Body', 'Black', 'Red'])

    if mat is None:
        # Create new if not found
        mat = bpy.data.materials.new(name='Mt_Body_Anthracite')
    else:
        # Rename existing
        mat.name = 'Mt_Body_Anthracite'

    # Ensure BSDF
    bsdf = ensure_bsdf_node(mat)

    # Update Metallic Anthracite properties
    bsdf.inputs['Base Color'].default_value = (*hex_to_rgb('#2F3133'), 1.0)
    safe_set_input(bsdf, 'Metallic', 1.0)
    safe_set_input(bsdf, 'Roughness', 0.5)

    print("✓ Mt_Body_Anthracite: #2F3133, Metallic 1.0, Roughness 0.5")
    return mat


def update_accents_material():
    """Update accents material to Safety Yellow."""
    # Find existing accents material
    mat = find_material_by_name(['Gunmetal', 'Leg', 'Accent', 'Stand'])

    if mat is None:
        # Create new if not found
        mat = bpy.data.materials.new(name='Mt_Accent_Yellow')
    else:
        # Rename existing
        mat.name = 'Mt_Accent_Yellow'

    # Ensure BSDF
    bsdf = ensure_bsdf_node(mat)

    # Update Safety Yellow properties
    bsdf.inputs['Base Color'].default_value = (*hex_to_rgb('#FFC400'), 1.0)
    safe_set_input(bsdf, 'Metallic', 0.0)  # Plastic, not metallic
    safe_set_input(bsdf, 'Roughness', 0.4)

    print("✓ Mt_Accent_Yellow: #FFC400, Metallic 0.0, Roughness 0.4")
    return mat


def update_logo_material():
    """Update logo material to Metallic Copper."""
    # Find existing logo material
    mat = find_material_by_name(['Badge', 'Logo', 'Text', 'LaserEtch', 'SilverGhost'])

    if mat is None:
        # Create new if not found
        mat = bpy.data.materials.new(name='Mt_Logo_Copper')
    else:
        # Rename existing
        mat.name = 'Mt_Logo_Copper'

    # Ensure BSDF
    bsdf = ensure_bsdf_node(mat)

    # Update Metallic Copper properties
    bsdf.inputs['Base Color'].default_value = (*hex_to_rgb('#B87333'), 1.0)
    safe_set_input(bsdf, 'Metallic', 1.0)  # Full metallic
    safe_set_input(bsdf, 'Roughness', 0.25)  # Polished

    print("✓ Mt_Logo_Copper: #B87333, Metallic 1.0, Roughness 0.25")
    return mat


def apply_materials_to_objects():
    """
    Apply the new materials to objects in the scene based on keyword matching.
    """
    # Get the materials
    body_mat = bpy.data.materials.get('Mt_Body_Anthracite')
    accent_mat = bpy.data.materials.get('Mt_Accent_Yellow')
    logo_mat = bpy.data.materials.get('Mt_Logo_Copper')

    applied = {'body': 0, 'accent': 0, 'logo': 0}

    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue

        name = obj.name.lower()

        # Apply body material to chassis/main body
        if any(k in name for k in ['chassis', 'body', 'main', 'case']):
            if body_mat:
                if len(obj.data.materials) > 0:
                    obj.data.materials[0] = body_mat
                else:
                    obj.data.materials.append(body_mat)
                applied['body'] += 1
            continue

        # Apply accent material to legs/end caps/connectors
        if any(k in name for k in ['leg', 'end_cap', 'connector', 'accent', 'stand', 'guide', 'plate']):
            if accent_mat:
                if len(obj.data.materials) > 0:
                    obj.data.materials[0] = accent_mat
                else:
                    obj.data.materials.append(accent_mat)
                applied['accent'] += 1
            continue

        # Apply logo material to badge/logo/text
        if any(k in name for k in ['badge', 'logo', 'text']):
            if logo_mat:
                if len(obj.data.materials) > 0:
                    obj.data.materials[0] = logo_mat
                else:
                    obj.data.materials.append(logo_mat)
                applied['logo'] += 1
            continue

    return applied


def main():
    """Execute the Spectra-Industrial Anthracite color scheme application."""
    print("=" * 60)
    print("SPECTRA-INDUSTRIAL SCHEME (ANTHRACITE VARIANT)")
    print("=" * 60)

    print("\n[1/3] METALLIC ANTHRACITE BODY")
    update_body_material()

    print("\n[2/3] SAFETY YELLOW ACCENTS")
    update_accents_material()

    print("\n[3/3] METALLIC COPPER LOGO")
    update_logo_material()

    print("\n[APPLYING MATERIALS TO OBJECTS]")
    applied = apply_materials_to_objects()
    print(f"  Body materials: {applied['body']}")
    print(f"  Accent materials: {applied['accent']}")
    print(f"  Logo materials: {applied['logo']}")

    print("\n" + "=" * 60)
    print("✓ Applied: Anthracite Body / Yellow Plastic / Copper Logo")
    print("=" * 60)


if __name__ == '__main__':
    main()
