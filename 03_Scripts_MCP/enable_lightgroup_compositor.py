import bpy

def ensure_compositor_tree():
    scene = bpy.context.scene
    scene.use_nodes = True
    tree = scene.node_tree
    return tree

def get_or_new_node(tree, node_type, name):
    for n in tree.nodes:
        if n.bl_idname == node_type and n.name == name:
            return n
    n = tree.nodes.new(node_type)
    n.name = name
    return n

def new_color_ramp(tree, name):
    """Create a compositor color ramp node with compatibility fallback."""
    for node_type in ('CompositorNodeColorRamp', 'CompositorNodeValToRGB'):
        if not hasattr(bpy.types, node_type):
            continue
        n = tree.nodes.new(node_type)
        n.name = name
        return n
    raise RuntimeError("No compositor Color Ramp node type available")

def setup_grade_nodes():
    tree = ensure_compositor_tree()
    for n in list(tree.nodes):
        if getattr(n, 'name', '') in {'RL_Dragon', 'CB_Grade', 'GL_Bloom', 'MX_Final', 'CMP_Out'}:
            tree.nodes.remove(n)

    rl = get_or_new_node(tree, 'CompositorNodeRLayers', 'RL_Dragon')
    cb = get_or_new_node(tree, 'CompositorNodeColorBalance', 'CB_Grade')
    gl = get_or_new_node(tree, 'CompositorNodeGlare', 'GL_Bloom')
    mx = get_or_new_node(tree, 'CompositorNodeMixRGB', 'MX_Final')
    cmp = get_or_new_node(tree, 'CompositorNodeComposite', 'CMP_Out')

    gl.inputs[1].default_value = 0.8
    gl.glare_type = 'FOG_GLOW'
    gl.quality = 'HIGH'
    mx.blend_type = 'MIX'
    mx.inputs[0].default_value = 1.0

    rl.location = (-600, 0)
    cb.location = (-300, 0)
    gl.location = (-100, 0)
    mx.location = (150, 0)
    cmp.location = (350, 0)

    links = tree.links
    links.new(rl.outputs['Image'], cb.inputs['Image'])
    links.new(cb.outputs['Image'], gl.inputs['Image'])
    links.new(gl.outputs['Image'], mx.inputs[2])
    links.new(rl.outputs['Image'], mx.inputs[1])
    links.new(mx.outputs['Image'], cmp.inputs['Image'])

    return rl, cb, gl, mx, cmp

def try_mix_lightgroups(rl, mx):
    lg_names = ['LG_Key', 'LG_Rim', 'LG_Fill']
    tree = bpy.context.scene.node_tree
    links = tree.links
    current = mx
    for lg in lg_names:
        sock = None
        for s in rl.outputs:
            if s.name == lg:
                sock = s
                break
        if sock is None:
            continue
        add = tree.nodes.new('CompositorNodeMixRGB')
        add.name = f'MX_{lg}'
        add.blend_type = 'ADD'
        add.inputs[0].default_value = 1.0
        add.location = current.location.x + 150, current.location.y - 150
        links.new(current.outputs['Image'], add.inputs[1])
        links.new(sock, add.inputs[2])
        current = add
    # Reconnect to Composite
    cmp = None
    for n in tree.nodes:
        if n.bl_idname == 'CompositorNodeComposite':
            cmp = n
            break
    if cmp:
        vg = tree.nodes.new('CompositorNodeEllipseMask')
        vg.name = 'VG_Mask'
        vg.width = 0.8
        vg.height = 0.8
        bl = tree.nodes.new('CompositorNodeBlur')
        bl.name = 'BL_Vig'
        bl.filter_type = 'GAUSS'
        bl.size_x = 150
        bl.size_y = 150
        cr = new_color_ramp(tree, 'CR_Vig')
        cr.color_ramp.elements[0].position = 0.0
        cr.color_ramp.elements[0].color = (0.85, 0.85, 0.85, 1.0)
        cr.color_ramp.elements[1].position = 1.0
        cr.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
        mxv = tree.nodes.new('CompositorNodeMixRGB')
        mxv.name = 'MX_Vig'
        mxv.blend_type = 'MULTIPLY'
        mxv.inputs[0].default_value = 1.0
        vg.location = current.location.x + 150, current.location.y + 100
        bl.location = vg.location.x + 150, vg.location.y
        cr.location = bl.location.x + 150, bl.location.y
        mxv.location = current.location.x + 300, current.location.y
        links.new(vg.outputs['Mask'], bl.inputs['Image'])
        links.new(bl.outputs['Image'], cr.inputs['Fac'])
        links.new(current.outputs['Image'], mxv.inputs[1])
        links.new(cr.outputs['Image'], mxv.inputs[2])
        links.new(mxv.outputs['Image'], cmp.inputs['Image'])

def enable_grade():
    rl, cb, gl, mx, cmp = setup_grade_nodes()
    try_mix_lightgroups(rl, mx)
    bpy.context.scene['grade_enabled'] = True

def disable_grade():
    tree = ensure_compositor_tree()
    rl = None
    cmp = None
    for n in tree.nodes:
        if n.bl_idname == 'CompositorNodeRLayers':
            rl = n
        if n.bl_idname == 'CompositorNodeComposite':
            cmp = n
    if rl and cmp:
        for l in list(tree.links):
            if l.to_node == cmp:
                tree.links.remove(l)
        tree.links.new(rl.outputs['Image'], cmp.inputs['Image'])
    bpy.context.scene['grade_enabled'] = False

def main():
    enable_grade()

if __name__ == '__main__':
    main()
