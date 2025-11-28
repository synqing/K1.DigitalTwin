import bpy
import os

def get_obj(name):
    return bpy.data.objects.get(name)

def ensure_focus_target():
    tgt = get_obj('Focus_Target')
    if tgt is None:
        tgt = bpy.data.objects.new('Focus_Target', None)
        tgt.location = (0.0, 0.0, 0.0)
        bpy.context.collection.objects.link(tgt)
    return tgt

def ensure_camera():
    cam_obj = get_obj('Cam_Hero_1')
    cam_data = None
    if cam_obj is not None and cam_obj.type == 'CAMERA':
        cam_data = cam_obj.data
    else:
        cam_data = bpy.data.cameras.get('Cam_Hero_1')
        if cam_data is None:
            cam_data = bpy.data.cameras.new(name='Cam_Hero_1')
        if cam_obj is None:
            cam_obj = bpy.data.objects.new('Cam_Hero_1', cam_data)
            bpy.context.collection.objects.link(cam_obj)
    cam_data.lens = 85.0
    cam_obj.location = (0.8, -0.8, 0.6)
    tgt = ensure_focus_target()
    track = None
    for c in cam_obj.constraints:
        if c.type == 'TRACK_TO' and c.target == tgt:
            track = c
            break
    if track is None:
        for c in list(cam_obj.constraints):
            if c.type == 'TRACK_TO':
                cam_obj.constraints.remove(c)
        track = cam_obj.constraints.new(type='TRACK_TO')
        track.target = tgt
        track.track_axis = 'TRACK_NEGATIVE_Z'
        track.up_axis = 'UP_Y'
    cam_data.dof.use_dof = True
    cam_data.dof.focus_object = tgt
    cam_data.dof.aperture_fstop = 4.0
    bpy.context.scene.camera = cam_obj
    return cam_obj, tgt

def ensure_light_groups():
    try:
        vl = bpy.context.view_layer
        lg_attr = getattr(vl, 'lightgroups', None)
        if lg_attr is None:
            return False
        def get_or_new(name):
            for lg in lg_attr:
                if lg.name == name:
                    return lg
            return lg_attr.new(name=name)
        lg_key = get_or_new('LG_Key')
        lg_rim = get_or_new('LG_Rim')
        lg_fill = get_or_new('LG_Fill')
        lg_env = get_or_new('LG_Env')
        def assign(obj_name, group_name):
            o = get_obj(obj_name)
            if o and o.type == 'LIGHT':
                try:
                    o.lightgroup = group_name
                except Exception:
                    pass
        assign('Key_Softbox', 'LG_Key')
        assign('Rim_Hero', 'LG_Rim')
        assign('Fill_Disk', 'LG_Fill')
        try:
            bpy.context.scene.world.lightgroup = 'LG_Env'
        except Exception:
            pass
        return True
    except Exception:
        return False

def hex_to_rgb(hex_str):
    s = hex_str.strip('#')
    return tuple(int(s[i:i+2], 16)/255.0 for i in (0, 2, 4))

def create_laser_etch_material():
    mat = bpy.data.materials.get('Mt_BadgeSteelLaserEtch')
    if mat is None:
        mat = bpy.data.materials.new(name='Mt_BadgeSteelLaserEtch')
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        for n in list(nodes):
            if n.type != 'OUTPUT_MATERIAL':
                nodes.remove(n)
        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        bsdf.location = (0, 0)
        bc = (*hex_to_rgb('E6E6E6'), 1.0)
        bsdf.inputs['Base Color'].default_value = bc
        bsdf.inputs['Metallic'].default_value = 1.0
        bsdf.inputs['Roughness'].default_value = 0.65
        bsdf.inputs['Anisotropic'].default_value = 0.0
        out = [n for n in nodes if n.type == 'OUTPUT_MATERIAL'][0]
        links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    return mat

def assign_laser_etch_to_logo():
    mat = create_laser_etch_material()
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        n = obj.name.lower()
        if 'logo' in n or 'text' in n:
            if len(obj.data.materials) == 0:
                obj.data.materials.append(mat)
            else:
                obj.data.materials[0] = mat

def main():
    ensure_camera()
    ensure_light_groups()
    assign_laser_etch_to_logo()
    cam = bpy.context.scene.camera
    if cam:
        print(f"ACTIVE CAMERA LOCATION: {tuple(cam.location)}")

if __name__ == '__main__':
    main()
