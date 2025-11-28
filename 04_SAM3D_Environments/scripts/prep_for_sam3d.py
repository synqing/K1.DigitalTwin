#!/usr/bin/env python3
"""
prep_for_sam3d.py - Image normalizer for SAM3/SAM3D pipeline

Normalises reference images:
- Ensures sRGB color space
- Resizes longest side to 2048 px (configurable)
- Saves to assets/reference/processed/
"""

import argparse
from pathlib import Path

from PIL import Image


def normalise_image(input_path: Path, output_path: Path, max_size: int = 2048) -> None:
    img = Image.open(input_path).convert("RGB")
    w, h = img.size
    scale = min(max_size / max(w, h), 1.0)
    if scale < 1.0:
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, format="JPEG", quality=95)
    print(f"Saved normalised image to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("env_name", help="environment name, e.g. battlestation_batman")
    parser.add_argument(
        "--max-size",
        type=int,
        default=2048,
        help="maximum dimension for the resized image",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    src = root / "assets" / "reference" / f"{args.env_name}.jpg"
    dst = root / "assets" / "reference" / "processed" / f"{args.env_name}.jpg"

    if not src.exists():
        raise SystemExit(f"Reference image not found: {src}")

    normalise_image(src, dst, max_size=args.max_size)


if __name__ == "__main__":
    main()
