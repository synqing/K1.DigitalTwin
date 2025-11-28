import os
from pathlib import Path

import bpy
from mathutils import Vector


def project_root() -> Path:
    try:
        return Path(__file__).resolve().parent.parent
    except NameError:
        cwd = Path.cwd()
        cand = cwd / "04_SAM3D_Environments"
        if cand.exists():
            return cand
        return Path("/Users/spectrasynq/K1-Lightwave_Digital-Twin/04_SAM3D_Environments")


def ref_image_path() -> Path:
    return project_root() / "assets" / "reference" / "kb_grey_flat.jpg"


def ensure_cycles():
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    cycles = scene.cycles
    cycles.feature_set = "SUPPORTED"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        if hasattr(prefs, "get_devices"):
            prefs.compute_device_type = "METAL"
        scene.cycles.device = "GPU"
    except Exception:
        scene.cycles.device = "CPU"


def ensure_scene(name: str) -> bpy.types.Scene:
    sc = bpy.data.scenes.get(name)
    if sc is None:
        sc = bpy.data.scenes.new(name)
    bpy.context.window.scene = sc
    return sc


def ensure_camera(name: str) -> bpy.types.Object:
    cam = bpy.data.objects.get(name)
    if cam is None:
        cam_data = bpy.data.cameras.new(name)
        cam = bpy.data.objects.new(name, cam_data)
        bpy.context.collection.objects.link(cam)
    cam.data.lens = 50.0
    cam.location = (0.0, -1.1, 0.5)
    cam.rotation_euler = (0.9, 0.0, 0.0)
    bpy.context.scene.camera = cam
    return cam


def set_units_metric():
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 1.0


def set_camera_background(cam: bpy.types.Object, img_path: Path):
    if not img_path.exists():
        raise FileNotFoundError(f"Missing reference image: {img_path}")
    img = bpy.data.images.get(img_path.name)
    if img is None:
        img = bpy.data.images.load(str(img_path))
    bg_list = cam.data.background_images
    if len(bg_list) == 0:
        bg = bg_list.new()
    else:
        bg = bg_list[0]
    bg.image = img
    bg.alpha = 1.0
    bg.show_background_image = True


def ensure_plane(name: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None:
        mesh = bpy.data.meshes.new(name)
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.primitive_plane_add()
        bpy.ops.object.mode_set(mode='OBJECT')
    return obj


def setup_geometry():
    desk = ensure_plane("Desk_kb_grey_flat")
    desk.location = (0.0, 0.0, 0.74)
    desk.scale = (0.9, 0.45, 1.0)
    return desk


def enable_shadow_catcher(obj: bpy.types.Object):
    obj.cycles.is_shadow_catcher = True
    bpy.context.scene.render.film_transparent = True


def exec_k1_master_build():
    repo_root = project_root().parent
    k1_path = repo_root / "03_Scripts_MCP" / "K1_MASTER_BUILD.py"
    if not k1_path.exists():
        raise FileNotFoundError("K1_MASTER_BUILD.py not found")
    exec(open(str(k1_path)).read(), {})


def find_k1_object() -> bpy.types.Object:
    candidates = ["K1", "K1_Lightwave", "K1.Body", "K1_Body", "K1_Chassis"]
    for name in candidates:
        obj = bpy.data.objects.get(name)
        if obj:
            return obj
    for obj in bpy.data.objects:
        if "k1" in obj.name.lower():
            return obj
    raise RuntimeError("K1 object not found after K1_MASTER_BUILD")


def ensure_k1_imported_from_blend() -> bool:
    blend_path = project_root().parent / "01_Blender_Production" / "K1.Hero.blend"
    if not blend_path.exists():
        return False
    for obj in bpy.data.objects:
        if "k1" in obj.name.lower():
            return True
    try:
        with bpy.data.libraries.load(str(blend_path), link=False) as (data_from, data_to):
            k1_object_names = [n for n in getattr(data_from, 'objects', []) if 'k1' in n.lower()]
            data_to.objects = k1_object_names
    except Exception:
        k1_object_names = []
    linked_any = False
    for obj in getattr(bpy.data, 'objects', []):
        if obj and ("k1" in obj.name.lower()):
            try:
                if obj.name not in {o.name for o in bpy.context.scene.collection.objects}:
                    bpy.context.scene.collection.objects.link(obj)
                linked_any = True
            except Exception:
                pass
    if not linked_any:
        try:
            with bpy.data.libraries.load(str(blend_path), link=False) as (data_from, data_to):
                k1_collections = [n for n in getattr(data_from, 'collections', []) if 'k1' in n.lower()]
            for col_name in k1_collections:
                try:
                    bpy.ops.wm.append(
                        filepath=str(blend_path / 'Collection' / col_name),
                        directory=str(blend_path / 'Collection'),
                        filename=col_name,
                    )
                    linked_any = True
                except Exception:
                    pass
        except Exception:
            pass
    return linked_any


def world_bbox(obj: bpy.types.Object):
    return [obj.matrix_world @ Vector(c) for c in obj.bound_box]


def align_obj_base_to_plane(obj: bpy.types.Object, plane: bpy.types.Object):
    bb = world_bbox(obj)
    min_z = min(v.z for v in bb)
    delta = plane.location.z - min_z
    obj.location.z += delta


def normalize_k1_physical_width(k1: bpy.types.Object, target_m: float = 0.345):
    k1_w = max(k1.dimensions.x, 1e-9)
    sf = target_m / k1_w
    k1.scale = (sf, sf, sf)


def scale_k1_for_plane(k1: bpy.types.Object, plane: bpy.types.Object, ratio: float = 0.35):
    w = plane.dimensions.x
    kw = max(k1.dimensions.x, 1e-6)
    sf = (w * ratio) / kw
    k1.scale = (sf, sf, sf)


def setup_lighting():
    for o in list(bpy.context.scene.objects):
        if o.type == 'LIGHT':
            bpy.data.objects.remove(o, do_unlink=True)
    key_data = bpy.data.lights.new(name='Key_top_left', type='AREA')
    key_data.shape = 'RECTANGLE'
    key_data.size = 1.0
    key_data.size_y = 0.5
    key_data.energy = 220.0
    key_data.color = (1.0, 0.97, 0.95)
    key_obj = bpy.data.objects.new('Key_top_left', key_data)
    bpy.context.collection.objects.link(key_obj)
    key_obj.location = (-0.7, -0.9, 1.0)
    fill_data = bpy.data.lights.new(name='Fill_front_right', type='AREA')
    fill_data.shape = 'DISK'
    fill_data.size = 2.0
    fill_data.energy = 100.0
    fill_data.color = (1.0, 0.98, 0.96)
    fill_obj = bpy.data.objects.new('Fill_front_right', fill_data)
    bpy.context.collection.objects.link(fill_obj)
    fill_obj.location = (0.7, 0.1, 1.2)


def setup_dof(cam: bpy.types.Object, focus_obj: bpy.types.Object):
    cam.data.dof.use_dof = True
    cam.data.dof.focus_object = focus_obj
    cam.data.dof.aperture_fstop = 3.2


def setup_compositor_background(img_path: Path):
    sc = bpy.context.scene
    sc.use_nodes = True
    nt = sc.node_tree
    nodes = nt.nodes
    links = nt.links
    for n in list(nodes):
        nodes.remove(n)
    rl = nodes.new('CompositorNodeRLayers')
    comp = nodes.new('CompositorNodeComposite')
    img_node = nodes.new('CompositorNodeImage')
    img_node.image = bpy.data.images.get(img_path.name) or bpy.data.images.load(str(img_path))
    alpha_over = nodes.new('CompositorNodeAlphaOver')
    alpha_over.inputs[0].default_value = 1.0
    rl.location = (-400, 0)
    img_node.location = (-400, -200)
    alpha_over.location = (-100, -100)
    comp.location = (200, -100)
    links.new(rl.outputs['Image'], alpha_over.inputs[1])
    links.new(img_node.outputs['Image'], alpha_over.inputs[2])
    links.new(alpha_over.outputs['Image'], comp.inputs['Image'])


def load_image(path: Path):
    if not path.exists():
        return None
    img = bpy.data.images.get(path.name)
    if img is None:
        img = bpy.data.images.load(str(path))
    return img


def mask_nonzero_ratio(img: bpy.types.Image) -> float:
    if img is None:
        return 0.0
    img.colorspace_settings.name = 'Non-Color'
    px = list(img.pixels)
    nonzero = 0
    total = int(len(px) / 4)
    for i in range(total):
        if px[i * 4] > 0.01:
            nonzero += 1
    return nonzero / max(total, 1)


def create_occluder(name: str, ref_img: bpy.types.Image, mask_img: bpy.types.Image) -> bpy.types.Object:
    obj = ensure_plane(name)
    obj.rotation_euler = (-1.5708, 0.0, 0.0)
    obj.location = (0.0, 0.12, 0.88)
    obj.scale = (1.3, 0.01, 0.9)
    mat = bpy.data.materials.get(f"Mat_{name}")
    if mat is None:
        mat = bpy.data.materials.new(name=f"Mat_{name}")
        mat.use_nodes = True
        nt = mat.node_tree
        nodes = nt.nodes
        links = nt.links
        for n in list(nodes):
            if n.type != 'OUTPUT_MATERIAL':
                nodes.remove(n)
        out = [n for n in nodes if n.type == 'OUTPUT_MATERIAL'][0]
        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        tex = nodes.new('ShaderNodeTexImage')
        tex.image = ref_img
        tex.extension = 'CLIP'
        tex_mask = nodes.new('ShaderNodeTexImage')
        tex_mask.image = mask_img
        tex_mask.extension = 'CLIP'
        tex_mask.image.colorspace_settings.name = 'Non-Color'
        texcoord = nodes.new('ShaderNodeTexCoord')
        mapping = nodes.new('ShaderNodeMapping')
        mapping.inputs['Scale'].default_value = (1.0, 1.0, 1.0)
        transparent = nodes.new('ShaderNodeBsdfTransparent')
        mix_shader = nodes.new('ShaderNodeMixShader')
        links.new(texcoord.outputs['Window'], mapping.inputs['Vector'])
        links.new(mapping.outputs['Vector'], tex.inputs['Vector'])
        links.new(mapping.outputs['Vector'], tex_mask.inputs['Vector'])
        links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
        links.new(tex_mask.outputs['Color'], mix_shader.inputs['Fac'])
        links.new(transparent.outputs['BSDF'], mix_shader.inputs[1])
        links.new(bsdf.outputs['BSDF'], mix_shader.inputs[2])
        links.new(mix_shader.outputs['Shader'], out.inputs['Surface'])
        mat.blend_method = 'BLEND'
    if len(obj.data.materials) == 0:
        obj.data.materials.append(mat)
    else:
        obj.data.materials[0] = mat
    return obj


def setup_occluders(img_path: Path):
    ref_img = load_image(img_path)
    masks_dir = project_root() / "assets" / "masks" / "kb_grey_flat"
    desk = bpy.data.objects.get("Desk_kb_grey_flat")

    def place_with_depth(obj: bpy.types.Object, kind: str):
        if kind in ("keyboard", "control_panel"):
            obj.location.z = (desk.location.z if desk else 0.74) + 0.02
        else:
            obj.location.z = (desk.location.z if desk else 0.74) + 0.05

    mask_names = ["keyboard.png", "control_panel.png"]
    for mn in mask_names:
        mp = masks_dir / mn
        mask_img = load_image(mp)
        if mask_img is None:
            continue
        ratio = mask_nonzero_ratio(mask_img)
        if ratio < 0.01:
            continue
        base = mn.split('.')[0]
        obj = create_occluder(f"Plane_{base}_occluder", ref_img, mask_img)
        place_with_depth(obj, base)


def tune_mood(cam: bpy.types.Object, k1: bpy.types.Object):
    key = bpy.data.objects.get('Key_top_left')
    fill = bpy.data.objects.get('Fill_front_right')
    if key and key.type == 'LIGHT':
        key.data.energy = 240.0
        key.data.color = (1.00, 0.96, 0.93)
    if fill and fill.type == 'LIGHT':
        fill.data.energy = 110.0
        fill.data.color = (1.00, 0.99, 0.97)
    k1.rotation_euler.z = -0.08
    cam.data.dof.aperture_fstop = 2.8


def render_kb_grey_flat_hero():
    out_dir = project_root() / "renders" / "kb_grey_flat"
    os.makedirs(out_dir, exist_ok=True)
    bpy.context.scene.render.filepath = str(out_dir / "kb_grey_flat_k1_hero.png")
    bpy.ops.render.render(write_still=True)


def main():
    img_path = ref_image_path()
    if not img_path.exists():
        raise FileNotFoundError("Copy zTEMP/kb_grey.jpg to assets/reference/kb_grey_flat.jpg")
    ensure_cycles()
    sc = ensure_scene("Composite_kb_grey_flat")
    set_units_metric()
    cam = ensure_camera("CAM_kb_grey_flat")
    set_camera_background(cam, img_path)
    desk = setup_geometry()
    enable_shadow_catcher(desk)
    exec_k1_master_build()
    ensure_k1_imported_from_blend()
    bpy.context.window.scene = sc
    k1 = find_k1_object()
    if k1.name not in {o.name for o in sc.collection.objects}:
        sc.collection.objects.link(k1)
    for obj in bpy.data.objects:
        if "k1" in obj.name.lower():
            if obj.name not in {o.name for o in sc.collection.objects}:
                sc.collection.objects.link(obj)
    normalize_k1_physical_width(k1, 0.345)
    scale_k1_for_plane(k1, desk, 0.38)
    k1.location.x = 0.0
    k1.location.y = 0.2
    align_obj_base_to_plane(k1, desk)
    setup_lighting()
    setup_dof(cam, k1)
    setup_occluders(img_path)
    tune_mood(cam, k1)
    setup_compositor_background(img_path)
    render_kb_grey_flat_hero()
    print("Created: scripts/build_kb_grey_flat_composite.py")
    print("Scene: Composite_kb_grey_flat, Camera: CAM_kb_grey_flat")
    print("Output: renders/kb_grey_flat/kb_grey_flat_k1_hero.png")


if __name__ == "__main__":
    main()
