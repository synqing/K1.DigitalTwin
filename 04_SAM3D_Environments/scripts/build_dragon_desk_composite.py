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
    return project_root() / "assets" / "reference" / "dragon_desk.jpg"


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
    cam.data.lens = 35.0
    cam.location = (0.0, -2.0, 1.3)
    cam.rotation_euler = (1.1, 0.0, 0.0)
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
    desk = ensure_plane("Desk_dragon")
    desk.location = (0.0, 0.0, 0.75)
    desk_width = 1.60
    desk_depth = 0.75
    desk.scale = (desk_width / 2.0, desk_depth / 2.0, 1.0)

    wall = ensure_plane("Wall_dragon")
    wall.location = (0.0, -0.1, 1.5)
    wall_width = 3.0
    wall_height = 2.5
    wall.scale = (wall_width / 2.0, 0.1, wall_height / 2.0)
    wall.rotation_euler = (0.0, 0.0, 0.0)

    return desk, wall


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
    candidates = [
        "K1",
        "K1_Lightwave",
        "K1.Body",
        "K1_Body",
        "K1_Chassis",
    ]
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

    # If K1 already present, nothing to do
    for obj in bpy.data.objects:
        if "k1" in obj.name.lower():
            return True

    # Try to load objects whose names include 'k1'
    try:
        with bpy.data.libraries.load(str(blend_path), link=False) as (data_from, data_to):
            k1_object_names = [n for n in getattr(data_from, 'objects', []) if 'k1' in n.lower()]
            data_to.objects = k1_object_names
    except Exception:
        k1_object_names = []

    linked_any = False
    for obj in getattr(bpy.data, 'objects', []):
        # Newly loaded objects may already be in bpy.data.objects but not linked to scene
        if obj and ("k1" in obj.name.lower()):
            try:
                if obj.name not in {o.name for o in bpy.context.scene.collection.objects}:
                    bpy.context.scene.collection.objects.link(obj)
                linked_any = True
            except Exception:
                pass

    # If no direct object match, attempt appending collections that include 'k1'
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

def place_k1_on_desk(k1: bpy.types.Object, desk: bpy.types.Object):
    k1.location = (0.0, 0.3, desk.location.z)


def world_bbox(obj: bpy.types.Object):
    return [obj.matrix_world @ Vector(c) for c in obj.bound_box]


def align_k1_to_desk(k1: bpy.types.Object, desk: bpy.types.Object):
    bb = world_bbox(k1)
    min_z = min(v.z for v in bb)
    delta = desk.location.z - min_z
    k1.location.z += delta
    k1.location.x = 0.0
    k1.location.y = 0.3


def scale_k1_for_desk(k1: bpy.types.Object, desk: bpy.types.Object, ratio: float = 0.35):
    desk_w = desk.dimensions.x
    k1_w = max(k1.dimensions.x, 1e-6)
    sf = (desk_w * ratio) / k1_w
    k1.scale = (sf, sf, sf)


def normalize_k1_physical_width(k1: bpy.types.Object, target_m: float = 0.345):
    k1_w = max(k1.dimensions.x, 1e-9)
    sf = target_m / k1_w
    k1.scale = (sf, sf, sf)


def ensure_k1_linked_to_scene(k1: bpy.types.Object, scene: bpy.types.Scene):
    names = {o.name for o in scene.collection.objects}
    if k1.name not in names:
        try:
            scene.collection.objects.link(k1)
        except Exception:
            pass


def ensure_all_k1_objects_linked(scene: bpy.types.Scene):
    for obj in bpy.data.objects:
        if "k1" in obj.name.lower():
            try:
                if obj.name not in {o.name for o in scene.collection.objects}:
                    scene.collection.objects.link(obj)
            except Exception:
                pass


def load_image(path: Path) -> bpy.types.Image | None:
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
        tex_mask = nodes.new('ShaderNodeTexImage')
        tex_mask.image = mask_img
        tex_mask.image.colorspace_settings.name = 'Non-Color'
        transparent = nodes.new('ShaderNodeBsdfTransparent')
        mix_shader = nodes.new('ShaderNodeMixShader')
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


def setup_occluders(ref_img: bpy.types.Image):
    masks_dir = project_root() / "assets" / "masks" / "dragon_desk"
    mask_names = ["monitor.png", "pc_tower.png", "foreground_object.png"]
    for mn in mask_names:
        mp = masks_dir / mn
        mask_img = load_image(mp)
        if mask_img is None:
            continue
        ratio = mask_nonzero_ratio(mask_img)
        print(f"Mask {mn}: {ratio:.3f} non-zero")
        if ratio < 0.01:
            continue
        base = mn.split('.')[0]
        obj = create_occluder(f"Plane_{base}_occluder", ref_img, mask_img)
        obj.location = (0.0, -0.05, 1.0)


def setup_lighting():
    for o in list(bpy.context.scene.objects):
        if o.type == 'LIGHT':
            bpy.data.objects.remove(o, do_unlink=True)
    key_data = bpy.data.lights.new(name='Key_monitor', type='AREA')
    key_data.shape = 'RECTANGLE'
    key_data.size = 1.0
    key_data.size_y = 0.5
    key_data.energy = 300.0
    key_data.color = (0.7, 0.9, 1.0)
    key_obj = bpy.data.objects.new('Key_monitor', key_data)
    bpy.context.collection.objects.link(key_obj)
    key_obj.location = (0.0, -1.0, 1.2)
    fill_data = bpy.data.lights.new(name='Fill_top', type='AREA')
    fill_data.shape = 'DISK'
    fill_data.size = 2.5
    fill_data.energy = 120.0
    fill_data.color = (1.0, 0.98, 0.95)
    fill_obj = bpy.data.objects.new('Fill_top', fill_data)
    bpy.context.collection.objects.link(fill_obj)
    fill_obj.location = (0.0, 0.0, 2.2)


def setup_dof(cam: bpy.types.Object, focus_obj: bpy.types.Object):
    cam.data.dof.use_dof = True
    cam.data.dof.focus_object = focus_obj
    cam.data.dof.aperture_fstop = 4.0


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


def render_dragon_desk_hero():
    out_dir = project_root() / "renders" / "dragon_desk"
    os.makedirs(out_dir, exist_ok=True)
    bpy.context.scene.render.filepath = str(out_dir / "dragon_desk_k1_hero.png")
    bpy.ops.render.render(write_still=True)


def main():
    img_path = ref_image_path()
    if not img_path.exists():
        raise FileNotFoundError("Copy zTEMP/dragon_desk.jpg to assets/reference/dragon_desk.jpg")
    ensure_cycles()
    sc = ensure_scene("Composite_DragonDesk")
    set_units_metric()
    cam = ensure_camera("CAM_dragon_desk")
    set_camera_background(cam, img_path)
    desk, wall = setup_geometry()
    enable_shadow_catcher(desk)
    exec_k1_master_build()
    ensure_k1_imported_from_blend()
    bpy.context.window.scene = sc
    k1 = find_k1_object()
    ensure_k1_linked_to_scene(k1, sc)
    ensure_all_k1_objects_linked(sc)
    normalize_k1_physical_width(k1, 0.345)
    scale_k1_for_desk(k1, desk)
    align_k1_to_desk(k1, desk)
    ref_img = load_image(img_path)
    setup_occluders(ref_img)
    setup_lighting()
    setup_dof(cam, k1)
    setup_compositor_background(img_path)
    render_dragon_desk_hero()
    print("Created: scripts/build_dragon_desk_composite.py")
    print("Scene: Composite_DragonDesk, Camera: CAM_dragon_desk")
    print("Output: renders/dragon_desk/dragon_desk_k1_hero.png")


if __name__ == "__main__":
    main()
