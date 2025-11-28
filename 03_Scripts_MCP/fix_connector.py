"""
fix_connector.py
K1-Lightwave Digital Twin - Satin Silver Connector Material

Creates and applies "Mt_Satin_Silver" to the center connector,
replacing cheap chrome with brushed/semi-polished aluminum aesthetic.

Material Physics:
- Roughness 0.35: Diffuses reflections (not a perfect mirror)
- Anisotropic 0.7: Simulates micro-grooves from machining
- Combined: Industrial precision, "jewel setting" for copper logo
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


def create_satin_silver_material():
    """
    Create or get the Mt_Satin_Silver material.
    Returns the material object.
    """
    mat = bpy.data.materials.get('Mt_Satin_Silver')

    if mat is None:
        # Create new material
        mat = bpy.data.materials.new(name='Mt_Satin_Silver')
    else:
        # Reset name if it was changed
        mat.name = 'Mt_Satin_Silver'

    # Ensure BSDF
    bsdf = ensure_bsdf_node(mat)

    # Set Satin Silver properties
    bsdf.inputs['Base Color'].default_value = (*hex_to_rgb('#E0E0E0'), 1.0)
    safe_set_input(bsdf, 'Metallic', 1.0)
    safe_set_input(bsdf, 'Roughness', 0.35)
    safe_set_input(bsdf, 'Anisotropic', 0.7)
    safe_set_input(bsdf, 'Anisotropic Rotation', 0.0)

    print("✓ Mt_Satin_Silver: #E0E0E0, Metallic 1.0, Roughness 0.35, Aniso 0.7")
    return mat


def is_connector(obj_name):
    """
    Check if object should be targeted as a connector.
    Returns True if name contains connector keywords AND is safe (not body/logo/leg).
    """
    name_lower = obj_name.lower()

    # Target keywords for connector
    connector_keywords = ['connect', 'bridge', 'middle', 'center', 'bracket', 'join']
    is_connector_obj = any(k in name_lower for k in connector_keywords)

    # Safety keywords to exclude
    exclude_keywords = ['logo', 'text', 'body', 'leg', 'leg', 'yellow', 'badge']
    is_excluded = any(k in name_lower for k in exclude_keywords)

    return is_connector_obj and not is_excluded


def apply_satin_silver_to_connectors():
    """
    Find and apply Mt_Satin_Silver material to connector objects.
    Returns list of objects that were updated.
    """
    mat = bpy.data.materials.get('Mt_Satin_Silver')
    if not mat:
        print("ERROR: Mt_Satin_Silver material not found!")
        return []

    applied_to = []

    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue

        if is_connector(obj.name):
            # Apply material
            if len(obj.data.materials) > 0:
                obj.data.materials[0] = mat
            else:
                obj.data.materials.append(mat)

            applied_to.append(obj.name)
            print(f"✓ Applied Satin Silver to: {obj.name}")

    return applied_to


def main():
    """Execute the Satin Silver connector material fix."""
    print("=" * 60)
    print("SATIN SILVER CONNECTOR MATERIAL")
    print("=" * 60)

    print("\n[1/2] CREATE SATIN SILVER MATERIAL")
    create_satin_silver_material()

    print("\n[2/2] APPLY TO CONNECTORS")
    applied = apply_satin_silver_to_connectors()

    if applied:
        print(f"\n✓ Material applied to {len(applied)} object(s)")
    else:
        print("\n⚠ No connector objects found matching criteria")
        print("  Search terms: 'connect', 'bridge', 'middle', 'center', 'bracket', 'join'")
        print("  Excluded: 'logo', 'text', 'body', 'leg', 'yellow', 'badge'")

    print("\n" + "=" * 60)
    print("✓ Satin Silver Connector Material Ready")
    print("=" * 60)


if __name__ == '__main__':
    main()
