"""Convert bilterm ``design_preview`` PPM frames into curated PNG fixtures plus a manifest.

Usage (normally invoked by ``scripts/capture_frames.sh``)::

    python -m bilterm_vr.capture --ppm-dir <dir of .ppm> --out fixtures/real [--bilterm-commit abc123]
"""

from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from typing import Optional

from PIL import Image

from .scenes import CURATED_FRAMES, FRAME_SIZE, parse_frame_name


def convert(ppm_dir: Path, out_dir: Path, bilterm_commit: Optional[str] = None) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    frames = {}
    for name in CURATED_FRAMES:
        src = ppm_dir / f"{name}.ppm"
        if not src.exists():
            raise FileNotFoundError(f"missing frame {src}; did design_preview run?")
        im = Image.open(src).convert("RGB")
        if im.size != FRAME_SIZE:
            raise ValueError(f"{name}: expected {FRAME_SIZE}, got {im.size}")
        dst = out_dir / f"{name}.png"
        im.save(dst, optimize=True)
        truth = parse_frame_name(name)
        (out_dir / f"{name}.json").write_text(json.dumps(truth.expected_answers(), indent=2) + "\n")
        frames[name] = {
            "style": truth.style,
            "theme": truth.theme,
            "scene": truth.scene,
            "layout": truth.layout,
            "drawer_visible": truth.drawer_visible,
            "pixel_sha256": hashlib.sha256(im.tobytes()).hexdigest(),
        }
    manifest = {
        "source": "bilterm examples/design_preview.rs (GuiWorkspaceRenderer, headless)",
        "bilterm_commit": bilterm_commit,
        "frame_size": list(FRAME_SIZE),
        "note": "<frame>.json files are idealised expected Jev answers derived from ground truth, not live model recordings.",
        "frames": frames,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ppm-dir", required=True, type=Path)
    p.add_argument("--out", default=Path("fixtures/real"), type=Path)
    p.add_argument("--bilterm-commit")
    a = p.parse_args()
    m = convert(a.ppm_dir, a.out, a.bilterm_commit)
    print(f"wrote {len(m['frames'])} frames + manifest to {a.out}")


if __name__ == "__main__":
    main()
