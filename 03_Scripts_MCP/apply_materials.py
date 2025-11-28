import bpy
import os
from mathutils import Vector

def open_master_scene():
    repo_root = os.path.dirname(os.path.dirname(__file__))
    blend_path = os.path.join(repo_root, '01_Blender_Production', 'K1_Master_Scene_v01.blend')
    if os.path.exists(blend_path):
        bpy.ops.wm.open_mainfile(filepath=blend_path)

def get_material(name):
    return bpy.data.materials.get(name)

def ensure_material_on_object(obj, mat):
    if obj.type != 'MESH' or mat is None:
        return False
    if len(obj.data.materials) == 0:
        obj.data.materials.append(mat)
    else:
        obj.data.materials[0] = mat
    return True

def matches(name, keywords):
    n = name.lower()
    return any(k.lower() in n for k in keywords)

def assign_materials_by_keywords():
    m_red = get_material('Mt_FoundersRed')
    m_gun = get_material('Mt_Gunmetal')
    m_badge = get_material('Mt_BadgeSteel')
    unassigned = []
    count_red = 0
    count_gun = 0
    count_badge = 0
    keyword_assigned = set()
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    for obj in meshes:
        if obj.type != 'MESH':
            continue
        name = obj.name
        if matches(name, ['Body', 'Chassis', 'Main', 'Case']):
            if ensure_material_on_object(obj, m_red):
                count_red += 1
                keyword_assigned.add(obj.name)
            else:
                unassigned.append(name)
            continue
        if matches(name, ['Leg', 'Stand', 'Screw', 'Bolt', 'USB', 'Port', 'Accent']):
            if ensure_material_on_object(obj, m_gun):
                count_gun += 1
                keyword_assigned.add(obj.name)
            else:
                unassigned.append(name)
            continue
        if matches(name, ['Badge', 'Logo', 'Text']):
            if ensure_material_on_object(obj, m_badge):
                count_badge += 1
                keyword_assigned.add(obj.name)
            else:
                unassigned.append(name)
            continue
    remaining = [o for o in meshes if o.name not in keyword_assigned]

    def world_bounds(obj):
        coords = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        min_x = min(c.x for c in coords)
        max_x = max(c.x for c in coords)
        min_y = min(c.y for c in coords)
        max_y = max(c.y for c in coords)
        min_z = min(c.z for c in coords)
        max_z = max(c.z for c in coords)
        dx = max_x - min_x
        dy = max_y - min_y
        dz = max_z - min_z
        volume = max(dx, 0) * max(dy, 0) * max(dz, 0)
        return (dx, dy, dz, volume)

    if remaining:
        sized = [(o, world_bounds(o)) for o in remaining]
        body_obj = max(sized, key=lambda t: t[1][3])[0]
        if ensure_material_on_object(body_obj, m_red):
            count_red += 1
            remaining = [o for o in remaining if o.name != body_obj.name]
        planar_candidates = []
        for o, dims in sized:
            if o.name == body_obj.name:
                continue
            dx, dy, dz, vol = dims
            if max(dx, dy, dz) == 0:
                continue
            ratio = min(dx, dy, dz) / max(dx, dy, dz)
            if ratio < 0.02:
                planar_candidates.append((o, vol))
        if planar_candidates:
            badge_obj = min(planar_candidates, key=lambda t: t[1])[0]
            if ensure_material_on_object(badge_obj, m_badge):
                count_badge += 1
                remaining = [o for o in remaining if o.name != badge_obj.name]
        for o in remaining:
            if ensure_material_on_object(o, m_gun):
                count_gun += 1
            else:
                unassigned.append(o.name)
    for name in unassigned:
        print(f"UNASSIGNED MESH: {name}")
    print(f"Assigned FoundersRed: {count_red}")
    print(f"Assigned Gunmetal: {count_gun}")
    print(f"Assigned BadgeSteel: {count_badge}")
    return unassigned

def setup_hero_camera():
    cam_data = bpy.data.cameras.new(name='Cam_Hero_1')
    cam_obj = bpy.data.objects.new('Cam_Hero_1', cam_data)
    bpy.context.collection.objects.link(cam_obj)
    cam_data.lens = 85.0
    cam_obj.location = (2.5, -3.5, 2.0)
    empty = bpy.data.objects.new('Focus_Target', None)
    empty.location = (0.0, 0.0, 0.0)
    bpy.context.collection.objects.link(empty)
    c = cam_obj.constraints.new(type='TRACK_TO')
    c.target = empty
    c.track_axis = 'TRACK_NEGATIVE_Z'
    c.up_axis = 'UP_Y'
    cam_data.dof.use_dof = True
    cam_data.dof.focus_object = empty
    cam_data.dof.aperture_fstop = 2.8
    bpy.context.scene.camera = cam_obj
    return cam_obj, empty

def set_output_path():
    bpy.context.scene.render.filepath = "//99_Render_Output/_drafts/K1_Test_Render_v01.png"
    out_dir = bpy.path.abspath("//99_Render_Output/_drafts")
    os.makedirs(out_dir, exist_ok=True)

def main():
    open_master_scene()
    unassigned = assign_materials_by_keywords()
    setup_hero_camera()
    set_output_path()
    # bpy.ops.render.render(write_still=True)
    return unassigned

if __name__ == '__main__':
    main()
