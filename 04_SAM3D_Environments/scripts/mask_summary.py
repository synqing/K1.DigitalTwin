import os
from pathlib import Path
from PIL import Image

def nonzero_pct(p: Path) -> float:
    img = Image.open(p).convert('L')
    arr = img.getdata()
    total = len(arr)
    nz = sum(1 for v in arr if v > 0)
    return (nz / max(total, 1)) * 100.0

def main() -> None:
    roots = [
        Path(__file__).resolve().parents[1] / "assets" / "masks" / "kb_wood_mat",
        Path(__file__).resolve().parents[1] / "assets" / "masks" / "kb_grey_flat",
    ]
    for mdir in roots:
        env = mdir.name
        print(f"Scene: {env}")
        if not mdir.exists():
            print(f"  Missing dir: {mdir}")
            continue
        for name in sorted(os.listdir(mdir)):
            p = mdir / name
            try:
                pct = nonzero_pct(p)
                print(f"  {name}: {pct:.2f}% non-zero")
            except Exception as e:
                print(f"  {name}: error {e}")
        print()

if __name__ == "__main__":
    main()
