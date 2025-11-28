Here’s a single, comprehensive prompt you can drop straight into the Claude Code / BlenderMCP agent to handle **this specific dragon-desk image** end-to-end.

You can tweak the scene name if you want, but this is ready to paste.

---

**ONE-SHOT PROMPT FOR AGENT**

You are working in the `04_SAM3D_Environments` project on my Mac.
We are NOT using SAM3D in this task, only **SAM3 (2D segmentation) + Blender compositing**.

Your job is to take a single reference image (the dragon gaming desk setup I’ve provided) and build a complete K1 Lightwave composite scene for it, end-to-end, using the existing project structure and scripts.

### 0. Scene name & file locations

1. Create / use the scene ID: **`dragon_desk`**.
2. Assume the reference image has been placed at:

   * `assets/reference/dragon_desk.jpg`

   If that file does not exist, stop and print a clear error telling me to copy the image there.

### 1. Image prep + SAM3 segmentation (Mac, local)

Use the existing Python env in this project (`.venv`) and the SAM3 scripts that already exist.

1. **Activate venv** (do this for any Python commands you run):

   ```bash
   cd 04_SAM3D_Environments
   source .venv/bin/activate
   ```

2. **Normalise the reference image** for SAM3/SAM3D compatibility using the existing script:

   ```bash
   python scripts/prep_for_sam3d.py dragon_desk --max-size 1024
   ```

   This should produce:

   * `assets/reference/processed/dragon_desk.jpg`

3. **Run SAM3 segmentation** using the existing `sam3_segment.py` (which already calls `facebook/sam3` and works on MPS):

   ```bash
   python scripts/sam3_segment.py dragon_desk \
     --prompts "desk surface" "monitor" "pc tower" "shelf" "foreground object"
   ```

   This should create binary PNG masks under:

   * `assets/masks/dragon_desk/desk_surface.png`
   * `assets/masks/dragon_desk/monitor.png`
   * `assets/masks/dragon_desk/pc_tower.png`
   * `assets/masks/dragon_desk/shelf.png`
   * `assets/masks/dragon_desk/foreground_object.png`

4. Quickly validate the masks programmatically (no GUI required):

   * For each mask, check that:

     * File exists.
     * At least ~1% of pixels are non-zero.
   * If any mask is completely empty or clearly broken, log a warning but **do not abort**; we can still use the working masks.

5. Print a short summary table in the console:

   * mask filename
   * % of non-zero pixels

### 2. Blender scene: build 2.5D composite for `dragon_desk`

Use **BlenderMCP** to control Blender via Python. Everything below should be executed by talking to Blender (not by hand).

Create a new script file:

* `scripts/build_dragon_desk_composite.py`

with the following responsibilities.

#### 2.1 Base scene and camera

In the script:

1. Ensure Cycles is the render engine, GPU if available.
2. Create a new scene or reuse an existing one named `Composite_DragonDesk`.
3. **Camera setup:**

   * If a camera named `CAM_dragon_desk` exists, reuse it; otherwise create it.
   * Settings:

     * Focal length: ~35 mm.
     * Position: slightly above and in front of the desk, similar to the photo angle.

       * e.g. location ≈ `(0.0, -2.0, 1.3)`
       * rotation ≈ `(1.1 rad, 0, 0)` (looking slightly downward).
   * Set this as the active camera.
4. **Background image:**

   * Set the camera background to `assets/reference/dragon_desk.jpg` (or the processed version if that’s easier).
   * Ensure it displays in camera view so object alignment is easy.

#### 2.2 Geometry: desk, wall, simple props

Still inside `build_dragon_desk_composite.py`:

1. **Desk plane:**

   * Add a plane named `Desk_dragon`.
   * In camera view, scale and position it so that:

     * Its top surface lines up with the visible desk surface in the background image.
   * Z ≈ desk height, e.g. `z = 0.75`.

2. **Wall plane:**

   * Add a plane named `Wall_dragon` behind the desk:

     * Large enough to cover the visible wall and hex panels in the photo.
   * Position e.g. at:

     * location ≈ `(0.0, -0.1, 1.5)` with orientation facing the camera.

3. **Optional occluder boxes (low-effort 3D):**

   * Add a simple box where the **PC tower** sits.
   * Optionally a shallow box where the monitor is, if we want 3D occlusion.
   * These don’t need perfect shape; they’re mainly for occlusion / lighting.

4. Assign temporary neutral materials to these objects (we’ll tweak later).

#### 2.3 Shadow catcher for desk

We want K1 to cast a realistic shadow onto the desk in the photo.

1. Set the material on `Desk_dragon` to a simple diffuse, and in the object’s Cycles settings mark it as a **Shadow Catcher** (object property, not world).
2. Confirm in the script that:

   * `Desk_dragon` is flagged as a shadow catcher.
   * The world background is transparent or uses Film → Transparent so the photo + shadow blending works cleanly.

#### 2.4 Bring in K1 Lightwave and place it

Use our existing master script:

1. In Blender, from the composite script, `exec` or import `K1_MASTER_BUILD.py` so the K1 model exists in the scene with its proper materials and dimensions.
2. Find the main K1 object/collection by name (e.g. any object whose name starts with `"K1"`).
3. Position it on the desk:

   * Place it roughly centered under the monitor, slightly forward on the desk plane.
   * Ensure its base sits exactly on `Desk_dragon` using the desk plane’s local Z as a reference (no floating or intersection).

Example (in code, adjust as needed):

* `k1.location = (0.0, 0.3, desk_height)` where `desk_height` is the Z of `Desk_dragon`’s surface.

4. Optionally rotate K1 slightly so the perspective matches the desk edges.

#### 2.5 Use SAM3 masks for occlusion (foreground planes)

To allow K1 to go *behind* certain objects (e.g. monitor, PC, foreground statue) we will use the SAM3 masks as alpha textures on image planes.

For each of these masks if available and non-empty:

* `monitor.png`
* `pc_tower.png`
* `foreground_object.png`

do the following:

1. Add a new plane for that object:

   * `Plane_monitor_occluder`, `Plane_pc_occluder`, etc.
   * Position each plane at the approximate depth of that object in the scene.
   * Use the same orientation as the wall or desk, whichever matches.
2. Create a new material for each occluder plane:

   * Base Color: use `dragon_desk.jpg` but UV-mapped so that the correct image portion covers the plane **AND** multiplied by the mask.
   * Alpha: use the corresponding mask PNG as alpha (white = visible).
   * Turn on Alpha Blend / Clip so the plane is transparent outside the mask.
3. The result should be:

   * From the camera’s point of view, the occluder plane matches the object in the photo.
   * Anything behind that plane (including K1) is hidden where the mask is white.

This gives us 2.5D occlusion using SAM3, without real 3D recon.

#### 2.6 Lighting to match the photo

In the same script, set up a simple but believable lighting rig:

1. Clear existing lights in this scene.
2. Add an **Area Light** named `Key_monitor`:

   * Place in front of the monitor, facing toward desk and K1.
   * Cool blue/cyan color to match monitor glow.
   * Medium intensity.
3. Add a subtle **back or top fill** light:

   * Warm or neutral, low intensity.
   * Just enough so K1 isn’t a black silhouette.

We don’t need perfect physical matching; just enough that K1 and its shadow feel integrated with the existing light in the photo.

#### 2.7 Camera & DOF

* Ensure `CAM_dragon_desk` is the scene camera.
* Enable depth of field:

  * Focus object: K1.
  * f-stop: ~4.0.

This will slightly blur background and foreground and help sell the composite.

### 3. Render setup & outputs

1. Set render engine to **Cycles**, resolution to match the reference image (e.g. 1920×1080 or the actual pixel size of `dragon_desk.jpg`).

2. Enable Film → Transparent if you plan to composite in 2D later; otherwise render the photo background directly in Blender.

3. Create a small render helper function or script inside `build_dragon_desk_composite.py`:

   * `render_dragon_desk_hero()`:

     * Ensures the scene is set up.
     * Renders a single frame from `CAM_dragon_desk`.
     * Saves output to `renders/dragon_desk/dragon_desk_k1_hero.png`.

4. After building the scene, **call** this render helper so I get at least one final image out.

### 4. Final report

When you’re done:

1. List all created / modified files:

   * The masks you produced.
   * `scripts/build_dragon_desk_composite.py`.
   * Any new materials or Blender scene names.
2. Confirm that:

   * You can open Blender, run:

     ```python
     exec(open('scripts/build_dragon_desk_composite.py').read())
     ```

     and get a valid scene with K1 on the dragon desk and at least one PNG render in `renders/dragon_desk/`.
3. If anything fails, print:

   * Exact traceback,
   * What you tried to do,
   * What manual fix you need from me (e.g. “missing reference image”, “mask is completely empty”, etc.).

---

Execute all of the above as a single cohesive task for the `dragon_desk` scene.
