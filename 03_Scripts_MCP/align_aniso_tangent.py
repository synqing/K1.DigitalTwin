import bpy

def get_principled(mat):
    if not mat or not mat.use_nodes:
        return None
    for n in mat.node_tree.nodes:
        if n.bl_idname == 'ShaderNodeBsdfPrincipled':
            return n
    return None

def enable_tangent_on_satin():
    mat = bpy.data.materials.get('Mt_Satin_Silver')
    if mat is None:
        return False
    bsdf = get_principled(mat)
    if bsdf is None:
        return False
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    # Remove existing links to Tangent input
    for l in list(links):
        if l.to_node == bsdf and l.to_socket.name == 'Tangent':
            links.remove(l)
    tan = nodes.get('Tangent_Satin')
    if tan is None:
        tan = nodes.new('ShaderNodeTangent')
        tan.name = 'Tangent_Satin'
        tan.location = bsdf.location.x - 200, bsdf.location.y - 150
    links.new(tan.outputs[0], bsdf.inputs['Tangent'])
    bpy.context.scene['satin_tangent_enabled'] = True
    return True

def disable_tangent_on_satin():
    mat = bpy.data.materials.get('Mt_Satin_Silver')
    if mat is None:
        return False
    bsdf = get_principled(mat)
    if bsdf is None:
        return False
    links = mat.node_tree.links
    for l in list(links):
        if l.to_node == bsdf and l.to_socket.name == 'Tangent':
            links.remove(l)
    bpy.context.scene['satin_tangent_enabled'] = False
    return True

def set_satin_tangent_axis(axis):
    mat = bpy.data.materials.get('Mt_Satin_Silver')
    if mat is None:
        return False
    bsdf = get_principled(mat)
    if bsdf is None:
        return False
    tan = None
    for n in mat.node_tree.nodes:
        if n.name == 'Tangent_Satin' and n.bl_idname == 'ShaderNodeTangent':
            tan = n
            break
    if tan is None:
        return False
    try:
        tan.axis = axis
    except Exception:
        return False
    return True

def set_satin_tangent_uv(uv_name):
    mat = bpy.data.materials.get('Mt_Satin_Silver')
    if mat is None:
        return False
    bsdf = get_principled(mat)
    if bsdf is None:
        return False
    tan = None
    for n in mat.node_tree.nodes:
        if n.name == 'Tangent_Satin' and n.bl_idname == 'ShaderNodeTangent':
            tan = n
            break
    if tan is None:
        return False
    try:
        tan.direction_type = 'UV_MAP'
        tan.uv_map = uv_name
    except Exception:
        return False
    return True

def main():
    enable_tangent_on_satin()

if __name__ == '__main__':
    main()
