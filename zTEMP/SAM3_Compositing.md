Alright, we ditch the dragon circus and start with the **easy wins**: these two close-up keyboard shots.

Below is a **single, comprehensive one-shot prompt** you can throw at the Claude Code / BlenderMCP agent to handle **both images** using SAM3 + Blender compositing.

I’ll name them:

* `kb_wood_mat`  → wooden-trim mech keyboard on black mat
* `kb_grey_flat` → low-profile grey keyboard on flat light desk

---

## ONE-SHOT PROMPT FOR AGENT (HANDLE BOTH KEYBOARD IMAGES)

You are working in the `04_SAM3D_Environments` project on my Mac.
We are **not** using SAM3D. Only **SAM3 (2D segmentation) + Blender compositing**.

Your job is to take **two reference images** (the keyboard desk shots I’ve provided) and build **two complete K1 Lightwave composite scenes**, end-to-end, using the existing project structure and scripts.

### 0. Scene IDs & file locations

Define two scene IDs:

* `kb_wood_mat`
* `kb_grey_flat`

Assume I will copy the images to:

* `assets/reference/kb_wood_mat.jpg`
* `assets/reference/kb_grey_flat.jpg`

If either file is missing, print a clear message telling me which path is missing and stop for that scene.

---

## 1. Image prep + SAM3 segmentation (Mac, local)

Use the existing `.venv` in `04_SAM3D_Environments` and the SAM3 script that’s already wired to `facebook/sam3` via `Sam3Model` / `Sam3Processor`.

For **both** scenes:

1. **Activate venv** for any Python commands:

   ```bash
   cd 04_SAM3D_Environments
   source .venv/bin/activate
   ```

2. **Normalise each reference image** (single pass; no resizing surprises later):

   ```bash
   python scripts/prep_for_sam3d.py kb_wood_mat  --max-size 1536
   python scripts/prep_for_sam3d.py kb_grey_flat --max-size 1536
   ```

   This should create:

   * `assets/reference/processed/kb_wood_mat.jpg`
   * `assets/reference/processed/kb_grey_flat.jpg`

3. **Run SAM3 segmentation** to get basic layout masks for each scene:

   For `kb_wood_mat`:

   ```bash
   python scripts/sam3_segment.py kb_wood_mat \
     --prompts "desk surface" "desk mat" "keyboard" "control panel"
   ```

   For `kb_grey_flat`:

   ```bash
   python scripts/sam3_segment.py kb_grey_flat \
     --prompts "desk surface" "keyboard" "control panel"
   ```

   This should produce binary PNG masks under:

   * `assets/masks/kb_wood_mat/desk_surface.png`

   * `assets/masks/kb_wood_mat/desk_mat.png`

   * `assets/masks/kb_wood_mat/keyboard.png`

   * `assets/masks/kb_wood_mat/control_panel.png`

   * `assets/masks/kb_grey_flat/desk_surface.png`

   * `assets/masks/kb_grey_flat/keyboard.png`

   * `assets/masks/kb_grey_flat/control_panel.png`

4. **Quick mask sanity check** (in Python, no GUI):

   For each mask:

   * Confirm the file exists.
   * Load it as an array and compute the fraction of non-zero pixels.

   If a mask is effectively empty (e.g. < 0.5% non-zero), log a warning like:

   > `WARN: mask kb_grey_flat/desk_mat.png appears empty (0.1% non-zero).`

   but **do not abort**; we can still build the scene without that layer.

5. Print a short table summarising for each scene:

   * mask filename
   * approximate % non-zero pixels

This checks SAM3 is behaving and gives us rough coverage without any human clicking.

---

## 2. Blender composites – 2.5D K1 placement for both images

Use Blender via BlenderMCP. You will create **two small builder scripts**:

* `scripts/build_kb_wood_mat_composite.py`
* `scripts/build_kb_grey_flat_composite.py`

Each script should be runnable from within Blender like:

```python
exec(open("scripts/build_kb_wood_mat_composite.py").read())
exec(open("scripts/build_kb_grey_flat_composite.py").read())
```

and produce:

* A complete scene with:

  * background photo,
  * minimal geometry (desk plane, optional mat),
  * K1 placed nicely in frame,
  * shadow catcher on desk,
  * simple lighting to match the photo.
* A rendered PNG per scene in `renders/<scene_id>/`.

### 2.1 Common behaviour for both builder scripts

For **each** script:

1. **Scene & render setup**

   * Create or use a scene named:

     * `Composite_kb_wood_mat` for the first script.
     * `Composite_kb_grey_flat` for the second script.
   * Set render engine to **Cycles**, use GPU if available.
   * Set resolution to match the reference image’s aspect ratio:

     * Use the actual pixel size of the processed image if you can read it, or 1536×1024-ish preserving aspect.

2. **Camera**

   * If a camera named `CAM_kb_wood_mat` / `CAM_kb_grey_flat` exists, reuse; otherwise create it.
   * Settings:

     * Focal length ≈ **50 mm** (tight product shot).
     * Position and rotation approximating the reference perspective:

       * For `kb_wood_mat`: camera low and slightly above the keyboard, angled down the mat.
       * For `kb_grey_flat`: camera just above deck, angled down so the empty foreground area is visible.
   * Set as active camera.

3. **Background image**

   * Attach the corresponding reference image as the **camera background**:

     * For `kb_wood_mat`: `assets/reference/kb_wood_mat.jpg` (or the processed version).
     * For `kb_grey_flat`: `assets/reference/kb_grey_flat.jpg`.
   * Ensure it displays in camera view so you can line up geometry.

4. **Geometry: desk + mat**

   Using the camera view with the background, add simple geometry:

   * **Desk plane**:

     * Add a plane named `Desk_<scene_id>`.
     * Position/scale so its top surface lines up with the visible desk/desk-mat area.
     * Z ≈ 0.75 or whatever matches the world origin.

   * For `kb_wood_mat` only:

     * Add a second plane named `DeskMat_kb_wood_mat`:

       * Slightly above the desk plane.
       * Sized/positioned to match the visible black desk mat region in the photo.

   These planes are just “invisible” geometry for shadows & lighting.

5. **Shadow catcher**

   For both scenes:

   * On the primary surface K1 will sit on (desk mat for `kb_wood_mat`, desk surface for `kb_grey_flat`):

     * In Cycles settings, mark that plane as a **Shadow Catcher** (object visibility flag).
   * This lets K1 cast realistic shadows onto the mat/desk when composited over the photo.

6. **Bring in K1 Lightwave**

   * Execute `K1_MASTER_BUILD.py` so the K1 model exists with its proper materials and scale.
   * Identify the main K1 object or collection by name (starts with `"K1"`).
   * Place K1 on the contact surface plane:

     * For `kb_wood_mat`: on the **front right half** of the mat (there is empty space in front/side of the existing keyboard).
     * For `kb_grey_flat`: in the **large empty foreground desk area** in front of the keyboard.
   * Ensure:

     * K1 base just touches the mat/desk (no intersection or floating).
     * Orientation matches perspective (use desk edges / keyboard as guides).
   * Scale K1 so it feels plausible next to the keyboard (e.g. ~40–60 cm wide visually; tweak by eye).

7. **Simple lighting to match each photo**

   Add a small number of lights to integrate K1 smoothly:

   * Clear any existing lights.

   For `kb_wood_mat`:

   * Add a **soft key light** coming from monitor direction (back/left):

     * Area Light, neutral/cool white.
   * Add a **subtle fill** from the opposite side so K1 isn’t pure silhouette.
   * Intensity: enough to see K1 and its shadow, but not so bright it looks disconnected from the existing photo lighting.

   For `kb_grey_flat`:

   * Single main **soft key** from top-left (same direction as the monitor/screen light).
   * Low-level fill from front-right.
   * Keep overall lighting soft and slightly warm to match the photo.

   We don’t need physical accuracy; just make K1 feel like it lives in that shot.

8. **Depth of Field**

   * Enable DOF on the camera:

     * Focus object = K1.
     * f-stop ≈ 2.8–4.0.
   * This should gently blur foreground/background so K1 is the crisp hero.

9. **Render helper in each script**

   Each builder script should define and then call a render helper:

   * `render_kb_wood_mat_hero()`
   * `render_kb_grey_flat_hero()`

   Each helper should:

   * Ensure the scene is set up.
   * Set output file path:

     * `renders/kb_wood_mat/kb_wood_mat_k1_hero.png`
     * `renders/kb_grey_flat/kb_grey_flat_k1_hero.png`
   * Trigger a single Cycles render from the scene’s camera.

   Use Film → Transparent if you want to preserve the option for 2D compositing later; otherwise you can render with the background image visible directly in Blender.

---

## 3. Execution order

1. In a shell (Mac):

   ```bash
   cd 04_SAM3D_Environments
   source .venv/bin/activate
   python scripts/prep_for_sam3d.py kb_wood_mat  --max-size 1536
   python scripts/prep_for_sam3d.py kb_grey_flat --max-size 1536
   python scripts/sam3_segment.py kb_wood_mat  --prompts "desk surface" "desk mat" "keyboard" "control panel"
   python scripts/sam3_segment.py kb_grey_flat --prompts "desk surface" "keyboard" "control panel"
   ```

2. In Blender (via MCP):

   ```python
   exec(open("scripts/build_kb_wood_mat_composite.py").read())
   exec(open("scripts/build_kb_grey_flat_composite.py").read())
   ```

Both scripts should:

* build their composite scenes,
* drop K1 in the right spot,
* and write the hero render PNGs into `renders/kb_wood_mat/` and `renders/kb_grey_flat/`.

---

## 4. Final report

When you’re done, print:

* The list of masks created for each scene and their non-zero percentages.
* The exact Blender scripts created/updated.
* The final render file paths for both scenes.
* Any limitations (e.g. if a particular mask was useless and ignored).

Execute all of the above as one cohesive task for the **two keyboard scenes** only.
