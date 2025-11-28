# SpectraSynq K1 - SAM3D Environment Pipeline

Rebuild real desk/gaming photos as Blender scenes with the **K1-Lightwave** as hero.

## Pipeline Overview

```
Reference JPEG -> prep_for_sam3d.py -> SAM3 segmentation -> SAM3D reconstruction -> Blender build -> Render
```

## Quick Start (with ML models)

```bash
# 1. Set up ML environment
conda create -n k1-ml python=3.11
conda activate k1-ml

# 2. Install dependencies
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install transformers accelerate pillow matplotlib numpy

# 3. Run pipeline for an environment
./run_k1_environment_pipeline.sh battlestation_batman

# 4. In Blender (via BlenderMCP):
#    - Run ../03_Scripts_MCP/K1_MASTER_BUILD.py
#    - Run scripts/build_battlestation_batman.py
```

## Quick Start (stub mode - no ML required)

```bash
# Uses placeholder masks/meshes - still generates valid manifests
source .venv/bin/activate
./run_k1_environment_pipeline.sh battlestation_batman
```

---

## ML Model Setup (Full Reconstruction)

### 1. PyTorch with MPS (Apple Silicon)

```bash
conda create -n k1-ml python=3.11
conda activate k1-ml

# PyTorch with MPS support (auto-detected on Apple Silicon)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install transformers accelerate pillow matplotlib numpy
```

Device selection pattern used in scripts:
```python
if torch.backends.mps.is_available():
    device = "mps"
elif torch.cuda.is_available():
    device = "cuda"
else:
    device = "cpu"
```

### 2. HuggingFace Model Access

Both models are gated by Meta. Request access:

1. **SAM3**: https://huggingface.co/facebook/sam3
   - Text-prompted segmentation
   - Used by `sam3_segment.py`

2. **SAM 3D Objects**: https://huggingface.co/facebook/sam-3d-objects
   - Single-image 3D reconstruction
   - Used by `sam3d_reconstruct.py`

Steps:
1. Log in to HuggingFace
2. Visit each model page
3. Click "Request Access"
4. Fill in required info (usually approved <24h)

### 3. SAM 3D Objects Repo Setup

SAM3D requires the GitHub repo (HF only hosts weights):

```bash
cd external/
git clone https://github.com/facebookresearch/sam-3d-objects.git
cd sam-3d-objects

# Install dependencies
pip install -r requirements.txt

# Download checkpoints (see their setup.md)
python scripts/download_checkpoints_hf.py  # or equivalent
```

Set environment variable:
```bash
export SAM3D_REPO_DIR=/path/to/sam-3d-objects
```

Or use default location: `04_SAM3D_Environments/external/sam-3d-objects/`

---

## Directory Structure

```
04_SAM3D_Environments/
├── assets/
│   ├── reference/          # Source JPEGs
│   │   └── processed/      # Normalized images (2048px max)
│   ├── masks/              # SAM3 segmentation output (PNG)
│   └── meshes/             # SAM3D reconstruction output (PLY/OBJ)
├── manifests/              # Scene manifests (JSON)
├── scripts/                # Python scripts
├── renders/                # Final renders
├── external/               # Cloned ML repos (sam-3d-objects)
└── .venv/                  # Python venv (stub mode)
```

---

## Scripts Reference

| Script | Purpose | ML Required |
|--------|---------|-------------|
| `prep_for_sam3d.py` | Normalize reference images | No (Pillow only) |
| `sam3_segment.py` | Generate masks (SAM3 -> SAM2 -> stub) | Optional |
| `sam3d_reconstruct.py` | Generate 3D meshes (SAM3D -> stub) | Optional |
| `build_environment_from_manifest.py` | Import meshes into Blender | No (Blender) |
| `build_battlestation_batman.py` | Build Batman environment | No (Blender) |
| `build_moody_laptop_desk.py` | Build moody desk environment | No (Blender) |

### Fallback Chain

**sam3_segment.py**:
1. Try SAM3 (text-prompted segmentation)
2. Fall back to SAM2 (automatic mask generation)
3. Fall back to stub (empty mask files)

**sam3d_reconstruct.py**:
1. Try SAM3D (3D reconstruction)
2. Fall back to stub (placeholder OBJ files)

---

## Environments

### battlestation_batman
Dark ultrawide gaming setup with monitor glow and RGB accents.

```bash
./run_k1_environment_pipeline.sh battlestation_batman
```

### moody_laptop_desk
Minimal desk lit by single warm lamp, deep shadows.

```bash
./run_k1_environment_pipeline.sh moody_laptop_desk
```

---

## Adding New Environments

1. Place reference image: `assets/reference/NEW_ENV.jpg`

2. Add prompts to shell script or run manually:
```bash
python scripts/prep_for_sam3d.py NEW_ENV
python scripts/sam3_segment.py NEW_ENV --prompts "desk" "chair" "monitor"
python scripts/sam3d_reconstruct.py NEW_ENV --objects desk chair monitor
```

3. Create Blender build script: `scripts/build_NEW_ENV.py`
   - Copy from existing environment script
   - Adjust lighting, camera, K1 position

---

## K1 Source of Truth

K1 geometry and materials live in `../03_Scripts_MCP/K1_MASTER_BUILD.py`.

Environment scripts:
- Position K1 in scene
- Set up environment lighting/camera
- **NEVER** redefine K1 materials or geometry

---

## Troubleshooting

### SAM3 not loading
```
[SAM3] SAM3 not available (missing imports)
```
- Install: `pip install transformers torch`
- Request HuggingFace access to `facebook/sam3`
- Login: `huggingface-cli login`

### SAM3D repo not found
```
[SAM3D] SAM3D repo not found
```
- Clone: `git clone https://github.com/facebookresearch/sam-3d-objects external/sam-3d-objects`
- Or set: `export SAM3D_REPO_DIR=/path/to/repo`

### Checkpoints missing
```
[SAM3D] SAM3D checkpoints not found
```
- Run checkpoint download script from sam-3d-objects repo
- Check `external/sam-3d-objects/checkpoints/hf/pipeline.yaml` exists

### MPS device issues
```
RuntimeError: MPS backend not available
```
- Update macOS to latest version
- Update PyTorch: `pip install --upgrade torch`
- Fallback: scripts auto-detect and use CPU

---

## License

Part of SpectraSynq K1-Lightwave Digital Twin project.

See `CLAUDE_SYSTEM_PROMPT.md` for agent brief.
