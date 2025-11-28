import bpy

def hex_to_rgb(hex_str):
    s = hex_str.strip('#')
    return tuple(int(s[i:i+2], 16)/255.0 for i in (0, 2, 4))

def get_or_create_material():
    mat = bpy.data.materials.get('Mt_SilverGhost')
    if mat is None:
        mat = bpy.data.materials.new(name='Mt_SilverGhost')
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        for n in list(nodes):
            if n.type != 'OUTPUT_MATERIAL':
                nodes.remove(n)
        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        bsdf.location = (0, 0)
        bsdf.inputs['Base Color'].default_value = (*hex_to_rgb('C8C8C8'), 1.0)

        # Set inputs with safe fallbacks for version compatibility
        def set_input(name, value):
            try:
                bsdf.inputs[name].default_value = value
            except (KeyError, AttributeError):
                pass  # Input doesn't exist in this Blender version

        set_input('Transmission', 0.95)
        set_input('Metallic', 0.3)
        set_input('Roughness', 0.3)
        set_input('IOR', 1.52)
        set_input('Alpha', 1.0)

        out = [n for n in nodes if n.type == 'OUTPUT_MATERIAL'][0]
        links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    return mat

def matches(name):
    n = name.lower()
    keys = ['guide', 'plate', 'lgp', 'diffuser']
    return any(k in n for k in keys)

def apply_material_to_targets():
    mat = get_or_create_material()
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        if matches(obj.name):
            if len(obj.data.materials) == 0:
                obj.data.materials.append(mat)
            else:
                obj.data.materials[0] = mat
            print(f"Applied Silver Ghost to: {obj.name}")

def set_camera_aperture():
    cam = bpy.data.objects.get('Cam_Hero_1')
    if cam and cam.type == 'CAMERA':
        cam.data.dof.use_dof = True
        cam.data.dof.aperture_fstop = 16.0
        print("Camera F-Stop set to f/16.0")

def main():
    apply_material_to_targets()
    set_camera_aperture()

if __name__ == '__main__':
    main()

