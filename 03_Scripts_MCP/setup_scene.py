import bpy
import math
import os

def set_render_settings():
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    cycles = scene.cycles
    cycles.feature_set = 'SUPPORTED'
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        if hasattr(prefs, 'get_devices'):
            prefs.compute_device_type = 'METAL' if bpy.app.build_platform == 'Darwin' else prefs.compute_device_type
        scene.cycles.device = 'GPU'
    except Exception:
        scene.cycles.device = 'CPU'
    cycles.samples = 1024
    cycles.preview_samples = 128
    cycles.max_bounces = 12
    cycles.diffuse_bounces = 4
    cycles.glossy_bounces = 6
    cycles.transmission_bounces = 12
    try:
        scene.view_settings.view_transform = 'AgX'
    except Exception:
        scene.view_settings.view_transform = scene.view_settings.view_transform
    scene.view_settings.look = 'Medium High Contrast'
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100

def set_world_background():
    scene = bpy.context.scene
    world = scene.world
    if world is None:
        world = bpy.data.worlds.new('World')
        scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nodes = nt.nodes
    links = nt.links
    bg = nodes.get('Background')
    out = nodes.get('World Output')
    if bg is None:
        bg = nodes.new('ShaderNodeBackground')
    if out is None:
        out = nodes.new('ShaderNodeOutputWorld')
    bg.inputs['Color'].default_value = (0.05, 0.05, 0.05, 1.0)
    if not bg.outputs['Background'].is_linked:
        links.new(bg.outputs['Background'], out.inputs['Surface'])

def hex_to_rgb(hex_str):
    hex_str = hex_str.strip('#')
    return tuple(int(hex_str[i:i+2], 16)/255.0 for i in (0, 2, 4))

def create_founders_red():
    mat = bpy.data.materials.new(name='Mt_FoundersRed')
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    for n in nodes:
        if n.type != 'OUTPUT_MATERIAL':
            nodes.remove(n)
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    bsdf.inputs['Base Color'].default_value = (*hex_to_rgb('540808'), 1.0)
    bsdf.inputs['Metallic'].default_value = 1.0
    bsdf.inputs['Roughness'].default_value = 0.45
    bump = nodes.new('ShaderNodeBump')
    bump.location = (-300, -150)
    bump.inputs['Strength'].default_value = 0.05
    bump.inputs['Distance'].default_value = 0.005
    noise = nodes.new('ShaderNodeTexNoise')
    noise.location = (-600, -150)
    noise.inputs['Scale'].default_value = 500.0
    noise.inputs['Detail'].default_value = 16.0
    links.new(noise.outputs['Fac'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    out = [n for n in nodes if n.type == 'OUTPUT_MATERIAL'][0]
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    return mat

def create_gunmetal():
    mat = bpy.data.materials.new(name='Mt_Gunmetal')
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    for n in nodes:
        if n.type != 'OUTPUT_MATERIAL':
            nodes.remove(n)
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    bsdf.inputs['Base Color'].default_value = (*hex_to_rgb('222222'), 1.0)
    bsdf.inputs['Metallic'].default_value = 1.0
    bsdf.inputs['Roughness'].default_value = 0.6
    bump = nodes.new('ShaderNodeBump')
    bump.location = (-300, -150)
    bump.inputs['Strength'].default_value = 0.03
    bump.inputs['Distance'].default_value = 0.005
    noise = nodes.new('ShaderNodeTexNoise')
    noise.location = (-600, -150)
    noise.inputs['Scale'].default_value = 500.0
    noise.inputs['Detail'].default_value = 16.0
    links.new(noise.outputs['Fac'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    out = [n for n in nodes if n.type == 'OUTPUT_MATERIAL'][0]
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    return mat

def create_badge_steel():
    mat = bpy.data.materials.new(name='Mt_BadgeSteel')
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    for n in nodes:
        if n.type != 'OUTPUT_MATERIAL':
            nodes.remove(n)
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    bsdf.inputs['Base Color'].default_value = (*hex_to_rgb('CCCCCC'), 1.0)
    bsdf.inputs['Metallic'].default_value = 1.0
    bsdf.inputs['Roughness'].default_value = 0.15
    bsdf.inputs['Anisotropic'].default_value = 0.8
    bsdf.inputs['Anisotropic Rotation'].default_value = 0.0
    out = [n for n in nodes if n.type == 'OUTPUT_MATERIAL'][0]
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    return mat

def delete_default_lights():
    objs = [o for o in bpy.context.scene.objects if o.type == 'LIGHT']
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)

def look_at(obj, target=(0.0, 0.0, 0.0)):
    dx = target[0] - obj.location[0]
    dy = target[1] - obj.location[1]
    dz = target[2] - obj.location[2]
    yaw = math.atan2(dx, dy)
    dist = math.sqrt(dx*dx + dy*dy)
    pitch = math.atan2(-dz, dist)
    obj.rotation_euler = (pitch, 0.0, yaw)

def create_area_light(name, shape, size_x, size_y, energy, color, location):
    light_data = bpy.data.lights.new(name=name, type='AREA')
    light_data.shape = shape
    if shape == 'RECTANGLE':
        light_data.size = size_x
        light_data.size_y = size_y
    else:
        light_data.size = size_x
    light_data.energy = energy
    light_data.color = color
    light_object = bpy.data.objects.new(name, light_data)
    bpy.context.collection.objects.link(light_object)
    light_object.location = location
    look_at(light_object)
    return light_object

def setup_lighting():
    delete_default_lights()
    create_area_light('Key_Softbox', 'RECTANGLE', 2.0, 2.0, 500.0, (1.0, 1.0, 1.0), (-3.0, 3.0, 3.0))
    create_area_light('Rim_Hero', 'RECTANGLE', 0.5, 2.0, 1200.0, (1.0, 1.0, 1.0), (0.0, -3.0, 3.0))
    create_area_light('Fill_Disk', 'DISK', 3.0, 3.0, 150.0, (*hex_to_rgb('E0E0FF'),), (3.0, 0.0, 2.0))

def list_scene_objects():
    names = [o.name for o in bpy.context.scene.objects]
    for n in names:
        print(n)
    return names

def main():
    repo_root = os.path.dirname(os.path.dirname(__file__))
    blend_path = os.path.join(repo_root, '01_Blender_Production', 'K1_Master_Scene_v01.blend')
    if os.path.exists(blend_path):
        bpy.ops.wm.open_mainfile(filepath=blend_path)
    set_render_settings()
    set_world_background()
    create_founders_red()
    create_gunmetal()
    create_badge_steel()
    setup_lighting()
    list_scene_objects()

if __name__ == '__main__':
    main()
