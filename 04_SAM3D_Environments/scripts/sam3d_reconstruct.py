#!/usr/bin/env python3
"""
sam3d_reconstruct.py

Real wrapper around Meta's SAM 3D Objects model (facebook/sam-3d-objects).

Frozen CLI interface:
  python scripts/sam3d_reconstruct.py ENV_NAME --objects obj1 obj2 ...

Inputs:
  assets/reference/processed/ENV_NAME.jpg
  assets/masks/ENV_NAME/<object>.png

Outputs:
  assets/meshes/ENV_NAME/<object>.ply (Gaussian splat)
  manifests/ENV_NAME_manifest.json

Implementation:
  1. Try real SAM3D via cloned sam-3d-objects repo
  2. Fallback to stub if repo/checkpoints unavailable

SETUP REQUIRED:
  1. Clone https://github.com/facebookresearch/sam-3d-objects
  2. Follow their setup instructions
  3. Set SAM3D_REPO_DIR env var (or use default: external/sam-3d-objects)
  4. Request HuggingFace access to facebook/sam-3d-objects
"""

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import List, Optional, Any

import numpy as np
from PIL import Image


log = logging.getLogger("sam3d_reconstruct")
logging.basicConfig(level=logging.INFO, format="[SAM3D] %(message)s")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class SceneObject:
    name: str
    mesh_path: str
    mask_path: str
    location: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation_euler: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])


# ============================================================================
# PATH & DEVICE UTILITIES
# ============================================================================

def get_project_root() -> Path:
    """Return 04_SAM3D_Environments/ root directory."""
    return Path(__file__).resolve().parents[1]


def get_device() -> str:
    """Get best available device for inference."""
    try:
        import torch
        if torch.backends.mps.is_available():
            log.info("Using MPS device (Apple Silicon)")
            return "mps"
        if torch.cuda.is_available():
            log.info("Using CUDA device")
            return "cuda"
    except ImportError:
        pass
    log.info("Using CPU device (may be slow)")
    return "cpu"


def get_sam3d_repo() -> Path:
    """Resolve SAM3D repo location, with env override."""
    env = os.getenv("SAM3D_REPO_DIR")
    if env:
        return Path(env).expanduser().resolve()
    # default: <project_root>/external/sam-3d-objects
    root = get_project_root()
    return (root / "external" / "sam-3d-objects").resolve()


def load_reference_image(env_name: str) -> Path:
    """Find and return path to reference image."""
    root = get_project_root()

    candidates = [
        root / "assets" / "reference" / "processed" / f"{env_name}.jpg",
        root / "assets" / "reference" / "processed" / f"{env_name}.png",
        root / "assets" / "reference" / f"{env_name}.jpg",
        root / "assets" / "reference" / f"{env_name}.png",
    ]

    for path in candidates:
        if path.exists():
            return path

    raise FileNotFoundError(f"No reference image found for '{env_name}'")


def load_mask_path(env_name: str, obj_name: str) -> Path:
    """Find mask file for a specific object."""
    root = get_project_root()
    mask_dir = root / "assets" / "masks" / env_name
    slug = obj_name.lower().replace(" ", "_")

    candidates = [
        mask_dir / f"{slug}.png",
        mask_dir / f"{slug}.jpg",
    ]

    for path in candidates:
        if path.exists():
            return path

    raise FileNotFoundError(f"No mask found for object '{obj_name}' in {mask_dir}")


def ensure_mesh_dir(env_name: str) -> Path:
    """Create and return mesh output directory."""
    root = get_project_root()
    mesh_dir = root / "assets" / "meshes" / env_name
    mesh_dir.mkdir(parents=True, exist_ok=True)
    return mesh_dir


# ============================================================================
# SAM3D REAL IMPLEMENTATION
# ============================================================================

def try_import_inference() -> Optional[Any]:
    """
    Try to import and initialize the SAM3D Inference class from cloned repo.
    Returns an Inference instance or None on failure.
    """
    repo = get_sam3d_repo()

    if not repo.exists():
        log.warning("SAM3D repo not found at %s", repo)
        log.warning("Clone it: git clone https://github.com/facebookresearch/sam-3d-objects %s", repo)
        return None

    # Check for checkpoint
    config_path = repo / "checkpoints" / "hf" / "pipeline.yaml"
    if not config_path.exists():
        log.warning("SAM3D checkpoints not found at %s", config_path)
        log.warning("Run the download script from the sam-3d-objects repo")
        return None

    # Add notebook directory to path for imports
    notebook_path = repo / "notebook"
    if str(notebook_path) not in sys.path:
        sys.path.insert(0, str(notebook_path))
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))

    try:
        from inference import Inference  # type: ignore[import-not-found]

        device = get_device()
        # compile=False is safer on MPS until tested
        inference = Inference(str(config_path), compile=False, device=device)
        log.info("SAM3D Inference loaded from %s", config_path)
        return inference

    except ImportError as e:
        log.warning("Failed to import SAM3D Inference: %s", e)
        log.warning("Ensure sam-3d-objects repo is set up correctly")
        return None
    except Exception as e:
        log.exception("Failed to initialize SAM3D Inference: %s", e)
        return None


def run_sam3d_for_object(
    env_name: str,
    obj_name: str,
    ref_image_path: Path,
    mask_path: Path,
    inference: Any,
) -> Path:
    """
    Run SAM3D reconstruction for a single object.

    Current implementation saves Gaussian splat as .ply file.
    """
    # Try to use SAM3D's own image loader if available
    try:
        from inference import load_image  # type: ignore[import-not-found]
        image = load_image(str(ref_image_path))
    except ImportError:
        # Fallback: load as numpy array
        image = np.array(Image.open(ref_image_path).convert("RGB"))

    # Load binary mask
    mask_img = Image.open(mask_path).convert("L")
    mask_arr = np.array(mask_img)
    mask_bool = mask_arr > 127

    # Check if mask has any content
    if not np.any(mask_bool):
        log.warning("Mask for '%s' is empty; reconstruction may fail", obj_name)

    log.info("Running SAM3D reconstruction for '%s'...", obj_name)

    try:
        # Run inference
        output = inference(image, mask_bool, seed=42)

        # Save Gaussian splat to PLY
        mesh_dir = ensure_mesh_dir(env_name)
        mesh_path = mesh_dir / f"{obj_name}.ply"

        if "gs" in output:
            output["gs"].save_ply(str(mesh_path))
            log.info("Saved Gaussian splat: %s", mesh_path)
        elif "mesh" in output:
            # Try mesh output if available
            output["mesh"].export(str(mesh_path))
            log.info("Saved mesh: %s", mesh_path)
        else:
            # Fallback: write placeholder
            log.warning("No recognizable output format; writing placeholder")
            mesh_path.write_text(f"# SAM3D output missing 'gs' or 'mesh' for {obj_name}\n")

        return mesh_path

    except Exception as e:
        log.exception("SAM3D reconstruction failed for '%s': %s", obj_name, e)
        # Write placeholder on failure
        mesh_dir = ensure_mesh_dir(env_name)
        mesh_path = mesh_dir / f"{obj_name}.ply"
        mesh_path.write_text(f"# SAM3D failed for {obj_name}: {e}\n")
        return mesh_path


# ============================================================================
# STUB FALLBACK
# ============================================================================

def run_stub(env_name: str, objects: List[str]) -> List[SceneObject]:
    """
    Fallback stub: creates placeholder mesh files and manifest.
    Maintains interface contract when SAM3D is unavailable.
    """
    root = get_project_root()
    mesh_dir = ensure_mesh_dir(env_name)
    scene_objects = []

    for obj_name in objects:
        slug = obj_name.lower().replace(" ", "_")
        mesh_path = mesh_dir / f"{slug}.obj"

        # Create placeholder OBJ
        if not mesh_path.exists():
            mesh_path.write_text(
                f"# Placeholder OBJ for {obj_name}\n"
                f"# TODO: Replace with SAM3D reconstruction\n"
                f"# Source environment: {env_name}\n"
            )

        log.warning("[STUB] Created placeholder mesh: %s", mesh_path)

        # Try to find mask path
        try:
            mask_path = load_mask_path(env_name, slug)
        except FileNotFoundError:
            mask_dir = root / "assets" / "masks" / env_name
            mask_path = mask_dir / f"{slug}.png"

        scene_objects.append(SceneObject(
            name=obj_name,
            mesh_path=str(mesh_path),
            mask_path=str(mask_path),
            location=[0.0, 0.0, 0.0],
            rotation_euler=[0.0, 0.0, 0.0],
            scale=[1.0, 1.0, 1.0],
        ))

    print("\n" + "=" * 60)
    print("[STUB] SAM3D model not available. Meshes are placeholders.")
    print("[STUB] To enable real reconstruction:")
    print("       1. Clone: git clone https://github.com/facebookresearch/sam-3d-objects")
    print("       2. Set up: cd sam-3d-objects && pip install -r requirements.txt")
    print("       3. Download checkpoints (see their README)")
    print("       4. Set: export SAM3D_REPO_DIR=/path/to/sam-3d-objects")
    print("=" * 60 + "\n")

    return scene_objects


# ============================================================================
# MAIN BACKEND
# ============================================================================

def run_sam3d_backend(env_name: str, objects: List[str]) -> List[SceneObject]:
    """
    Run SAM3D reconstruction with fallback to stub.
    """
    inference = try_import_inference()

    if inference is None:
        log.warning("SAM3D unavailable, falling back to stub")
        return run_stub(env_name, objects)

    # Real SAM3D path
    ref_image_path = load_reference_image(env_name)
    scene_objects = []

    for obj_name in objects:
        slug = obj_name.lower().replace(" ", "_")

        try:
            mask_path = load_mask_path(env_name, slug)
        except FileNotFoundError as e:
            log.warning("Mask not found for '%s': %s; skipping", obj_name, e)
            continue

        mesh_path = run_sam3d_for_object(
            env_name, slug, ref_image_path, mask_path, inference
        )

        scene_objects.append(SceneObject(
            name=obj_name,
            mesh_path=str(mesh_path),
            mask_path=str(mask_path),
            location=[0.0, 0.0, 0.0],
            rotation_euler=[0.0, 0.0, 0.0],
            scale=[1.0, 1.0, 1.0],
        ))

    return scene_objects


def write_manifest(env_name: str, objects: List[SceneObject]) -> Path:
    """Write scene manifest JSON file."""
    root = get_project_root()

    try:
        ref_image_path = load_reference_image(env_name)
    except FileNotFoundError:
        ref_image_path = root / "assets" / "reference" / f"{env_name}.jpg"

    manifest = {
        "env_name": env_name,
        "reference_image": str(ref_image_path),
        "objects": [asdict(o) for o in objects],
        "notes": "Generated by sam3d_reconstruct.py. Transforms are placeholders.",
    }

    manifest_dir = root / "manifests"
    manifest_dir.mkdir(exist_ok=True)
    manifest_path = manifest_dir / f"{env_name}_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    log.info("Wrote manifest: %s", manifest_path)
    return manifest_path


# ============================================================================
# MAIN CLI
# ============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="SAM3D reconstruction wrapper with fallback to stub"
    )
    parser.add_argument(
        "env_name",
        help="Environment name (e.g., battlestation_batman)"
    )
    parser.add_argument(
        "--objects",
        nargs="+",
        required=True,
        help="Object names matching mask files (e.g., gaming_chair desk_surface)"
    )
    args = parser.parse_args()

    # Run reconstruction
    scene_objects = run_sam3d_backend(args.env_name, args.objects)

    # Write manifest
    write_manifest(args.env_name, scene_objects)


if __name__ == "__main__":
    main()
