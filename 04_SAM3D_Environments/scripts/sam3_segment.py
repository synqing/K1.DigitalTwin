#!/usr/bin/env python3
"""
sam3_segment.py

Real wrapper around Meta's SAM 3 model via Hugging Face.

Frozen CLI interface:
  python scripts/sam3_segment.py ENV_NAME --prompts "object1" "object2" ...

Outputs:
  assets/masks/ENV_NAME/<prompt_slug>.png  (single-channel, 0=bg, 255=object)

Implementation priority:
  1. Try real SAM3 model via transformers (Sam3Model + Sam3Processor)
  2. Fallback to SAM2 automatic mask generation if SAM3 unavailable
  3. Fallback to stub if no models available

Requires:
- transformers >= 4.46 (SAM3 support)
- torch with MPS or CUDA or CPU
- Hugging Face access to facebook/sam3 (gated by Meta)
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional, Any

import numpy as np
from PIL import Image

log = logging.getLogger("sam3_segment")
logging.basicConfig(level=logging.INFO, format="[SAM3] %(message)s")


# ============================================================================
# CONFIGURATION
# ============================================================================

# Model IDs (in preference order)
SAM3_MODEL_ID = "facebook/sam3"
SAM2_MODEL_ID = "facebook/sam2-hiera-large"


# ============================================================================
# DEVICE DETECTION
# ============================================================================

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
    log.info("Using CPU device")
    return "cpu"


def get_torch_device():
    """Get torch.device object."""
    import torch
    device_str = get_device()
    return torch.device(device_str)


# ============================================================================
# PATH UTILITIES
# ============================================================================

def get_project_root() -> Path:
    """Return 04_SAM3D_Environments/ root directory."""
    return Path(__file__).resolve().parents[1]


def ensure_mask_dir(env_name: str) -> Path:
    """Create and return mask output directory."""
    root = get_project_root()
    mask_dir = root / "assets" / "masks" / env_name
    mask_dir.mkdir(parents=True, exist_ok=True)
    return mask_dir


def load_reference_image(env_name: str) -> Image.Image:
    """Load reference image, preferring processed version."""
    root = get_project_root()

    candidates = [
        root / "assets" / "reference" / "processed" / f"{env_name}.jpg",
        root / "assets" / "reference" / "processed" / f"{env_name}.png",
        root / "assets" / "reference" / f"{env_name}.jpg",
        root / "assets" / "reference" / f"{env_name}.png",
    ]

    for path in candidates:
        if path.exists():
            log.info("Loading reference image: %s", path)
            return Image.open(path).convert("RGB")

    raise FileNotFoundError(
        f"No reference image found for '{env_name}' in assets/reference/"
    )


def slugify_prompt(prompt: str) -> str:
    """Convert prompt to filename-safe slug."""
    return prompt.strip().lower().replace(" ", "_")


def save_binary_mask(mask: np.ndarray, out_path: Path) -> None:
    """Save boolean/binary mask as 8-bit PNG (0/255)."""
    if mask.ndim == 3:
        mask = mask[0]  # Take first channel if multi-channel
    mask_uint8 = (mask.astype(np.uint8) * 255)
    img = Image.fromarray(mask_uint8, mode="L")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    log.info("Saved mask: %s", out_path)


# ============================================================================
# SAM3 REAL IMPLEMENTATION (Text-Prompted PCS)
# ============================================================================

def try_load_sam3() -> Optional[tuple[Any, Any]]:
    """
    Try to load SAM3 model and processor from HuggingFace.
    Returns (model, processor) tuple or None if unavailable.
    """
    try:
        import torch
        from transformers import Sam3Model, Sam3Processor

        device = get_torch_device()
        log.info("Loading SAM3 model from %s...", SAM3_MODEL_ID)

        model = Sam3Model.from_pretrained(SAM3_MODEL_ID).to(device)
        processor = Sam3Processor.from_pretrained(SAM3_MODEL_ID)

        log.info("SAM3 model loaded successfully on %s", device)
        return model, processor

    except ImportError as e:
        log.warning("SAM3 not available (missing imports): %s", e)
        return None
    except Exception as e:
        log.warning("SAM3 failed to load: %s", e)
        return None


def run_sam3_real(
    env_name: str,
    prompts: list[str],
    model: Any,
    processor: Any,
) -> list[Path]:
    """
    Run real SAM3 text-prompted segmentation.

    Uses Sam3Model + Sam3Processor for Promptable Concept Segmentation (PCS).
    """
    import torch

    device = get_torch_device()
    image = load_reference_image(env_name)
    mask_dir = ensure_mask_dir(env_name)
    masks_created = []

    for prompt in prompts:
        slug = slugify_prompt(prompt)
        out_path = mask_dir / f"{slug}.png"

        log.info("Running SAM3 for prompt '%s' -> %s", prompt, out_path.name)

        # Build inputs: text-only PCS
        inputs = processor(
            images=image,
            text=prompt,
            return_tensors="pt",
        ).to(device)

        with torch.no_grad():
            outputs = model(**inputs)

        # Post-process to instance masks at original resolution
        try:
            # Get original sizes for proper upscaling
            original_sizes = inputs.get("original_sizes")
            if original_sizes is not None:
                target_sizes = original_sizes.tolist()
            else:
                target_sizes = [list(image.size[::-1])]  # [H, W]

            results = processor.post_process_instance_segmentation(
                outputs,
                threshold=0.5,
                mask_threshold=0.5,
                target_sizes=target_sizes,
            )[0]

            masks = results.get("masks")  # tensor [N, H, W]

            if masks is None or masks.numel() == 0:
                log.warning("No masks returned for prompt '%s'; writing empty mask", prompt)
                w, h = image.size
                empty = np.zeros((h, w), dtype=np.uint8)
                Image.fromarray(empty, mode="L").save(out_path)
            else:
                # Combine all instances into a single mask (logical OR)
                combined = torch.any(masks > 0.5, dim=0).cpu().numpy()
                save_binary_mask(combined, out_path)

        except Exception as e:
            log.warning("Post-processing failed for '%s': %s; writing empty mask", prompt, e)
            w, h = image.size
            empty = np.zeros((h, w), dtype=np.uint8)
            Image.fromarray(empty, mode="L").save(out_path)

        masks_created.append(out_path)

    return masks_created


# ============================================================================
# SAM2 FALLBACK (Automatic Mask Generation)
# ============================================================================

def try_load_sam2_pipeline() -> Optional[Any]:
    """
    Try to load SAM2 automatic mask generation pipeline.
    Returns pipeline or None if unavailable.
    """
    try:
        from transformers import pipeline

        device = get_device()
        log.info("Loading SAM2 pipeline from %s...", SAM2_MODEL_ID)

        try:
            pipe = pipeline("mask-generation", model=SAM2_MODEL_ID, device=device)
        except Exception:
            # Fallback to CPU if device fails
            pipe = pipeline("mask-generation", model=SAM2_MODEL_ID, device="cpu")

        log.info("SAM2 pipeline loaded successfully")
        return pipe

    except ImportError as e:
        log.warning("SAM2 not available (missing imports): %s", e)
        return None
    except Exception as e:
        log.warning("SAM2 failed to load: %s", e)
        return None


def run_sam2_automatic(
    env_name: str,
    prompts: list[str],
    pipe: Any,
) -> list[Path]:
    """
    Run SAM2 automatic mask generation as fallback.

    Note: SAM2 doesn't support text prompts directly.
    We generate all masks and assign to prompts by area (largest first).
    """
    image = load_reference_image(env_name)
    mask_dir = ensure_mask_dir(env_name)
    masks_created = []

    log.info("Running SAM2 automatic mask generation...")

    try:
        outputs = pipe(image, points_per_batch=64)
        masks = outputs.get("masks", [])
    except Exception as e:
        log.warning("SAM2 inference failed: %s", e)
        masks = []

    # Sort masks by area (largest first)
    if masks:
        mask_areas = [(i, np.sum(m)) for i, m in enumerate(masks)]
        mask_areas.sort(key=lambda x: x[1], reverse=True)
    else:
        mask_areas = []

    for i, prompt in enumerate(prompts):
        slug = slugify_prompt(prompt)
        out_path = mask_dir / f"{slug}.png"

        if i < len(mask_areas):
            mask_idx = mask_areas[i][0]
            mask_array = (np.array(masks[mask_idx]) * 255).astype(np.uint8)
            Image.fromarray(mask_array, mode="L").save(out_path)
            log.info("Saved mask: %s (area: %d)", out_path.name, mask_areas[i][1])
        else:
            # Not enough masks - create empty placeholder
            w, h = image.size
            empty = np.zeros((h, w), dtype=np.uint8)
            Image.fromarray(empty, mode="L").save(out_path)
            log.warning("No mask available for '%s'; created empty mask", prompt)

        masks_created.append(out_path)

    return masks_created


# ============================================================================
# STUB FALLBACK
# ============================================================================

def run_stub(env_name: str, prompts: list[str]) -> list[Path]:
    """
    Final fallback: creates empty mask files with correct filenames.
    Maintains interface contract when no models are available.
    """
    mask_dir = ensure_mask_dir(env_name)
    masks_created = []

    for prompt in prompts:
        slug = slugify_prompt(prompt)
        out_path = mask_dir / f"{slug}.png"

        if not out_path.exists():
            out_path.write_bytes(b"")  # Empty placeholder

        log.warning("[STUB] Created placeholder mask for '%s' at %s", prompt, out_path)
        masks_created.append(out_path)

    print("\n" + "=" * 60)
    print("[STUB] SAM3/SAM2 models not available. Masks are placeholders.")
    print("[STUB] To enable real segmentation:")
    print("       conda create -n k1-ml python=3.11")
    print("       conda activate k1-ml")
    print("       pip install torch torchvision transformers pillow numpy")
    print("       # Request access to facebook/sam3 on HuggingFace")
    print("=" * 60 + "\n")

    return masks_created


# ============================================================================
# MAIN ORCHESTRATION
# ============================================================================

def run_segmentation(env_name: str, prompts: list[str]) -> list[Path]:
    """
    Run segmentation with automatic fallback chain:
    1. Try SAM3 (text-prompted)
    2. Try SAM2 (automatic mask generation)
    3. Fall back to stub
    """
    # Try SAM3 first (best: text-prompted)
    sam3_result = try_load_sam3()
    if sam3_result is not None:
        model, processor = sam3_result
        try:
            return run_sam3_real(env_name, prompts, model, processor)
        except Exception as e:
            log.exception("SAM3 inference failed: %s", e)

    # Try SAM2 fallback (automatic masks)
    sam2_pipe = try_load_sam2_pipeline()
    if sam2_pipe is not None:
        try:
            return run_sam2_automatic(env_name, prompts, sam2_pipe)
        except Exception as e:
            log.exception("SAM2 inference failed: %s", e)

    # Final fallback: stub
    return run_stub(env_name, prompts)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SAM3 segmentation wrapper with automatic fallback"
    )
    parser.add_argument("env_name", help="Environment name (e.g., battlestation_batman)")
    parser.add_argument(
        "--prompts",
        nargs="+",
        required=True,
        help='Object prompts, e.g., "gaming chair" "desk surface"'
    )
    args = parser.parse_args()

    # Verify reference image exists
    root = get_project_root()
    candidates = [
        root / "assets" / "reference" / "processed" / f"{args.env_name}.jpg",
        root / "assets" / "reference" / f"{args.env_name}.jpg",
    ]

    if not any(c.exists() for c in candidates):
        log.error("Reference image not found for '%s'", args.env_name)
        log.error("Checked: %s", [str(c) for c in candidates])
        sys.exit(1)

    # Run segmentation with fallback chain
    run_segmentation(args.env_name, args.prompts)


if __name__ == "__main__":
    main()
