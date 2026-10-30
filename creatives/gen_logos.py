#!/usr/bin/env python3
"""
gen_logos.py  —  Convert SVG placeholder logos to PNG for use in HTML templates.

Requires: cairosvg  OR  inkscape/rsvg-convert on PATH  OR  Pillow (fallback text logo)

Usage:
    python gen_logos.py
    python gen_logos.py --height 200
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR  = Path(__file__).parent
LOGOS_DIR   = SCRIPT_DIR / "logos"

LOGOS = [
    {"svg": "ne_mark.svg",  "png": "ne_mark.png"},
    {"svg": "bizwrap.svg",  "png": "bizwrap.png"},
    {"svg": "cgi.svg",      "png": "cgi.png"},
]


def svg_to_png_cairosvg(svg_path: Path, png_path: Path, height: int = 120):
    try:
        import cairosvg
        cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), output_height=height)
        return True
    except ImportError:
        return False
    except Exception as e:
        print(f"[logos] cairosvg error: {e}", file=sys.stderr)
        return False


def svg_to_png_inkscape(svg_path: Path, png_path: Path, height: int = 120) -> bool:
    for exe in ("inkscape", "rsvg-convert"):
        if not shutil.which(exe):
            continue
        if exe == "inkscape":
            cmd = [exe, f"--export-filename={png_path}", f"--export-height={height}", str(svg_path)]
        else:
            cmd = [exe, "-h", str(height), "-o", str(png_path), str(svg_path)]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode == 0:
            return True
    return False


def fallback_text_logo(name: str, png_path: Path, height: int = 120):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("[logos] Pillow not installed — cannot create fallback PNG.", file=sys.stderr)
        return False

    colors = {"ne": ("#1A2C4E","#D4A017"), "bi": ("#2D5016","#F4C430"), "cg": ("#4A1C6B","#C0A060")}
    key = name[:2].lower()
    bg, fg = colors.get(key, ("#333", "#fff"))

    w = height
    img = Image.new("RGBA", (w, height), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, w-4, height-4], fill=bg)
    initials = name[:2].upper()
    draw.text((w//2, height//2), initials, fill=fg, anchor="mm")
    img.save(str(png_path), "PNG")
    return True


def main():
    parser = argparse.ArgumentParser(description="Convert SVG logos to PNG.")
    parser.add_argument("--height", type=int, default=120, help="Output height in pixels (default 120)")
    args = parser.parse_args()

    LOGOS_DIR.mkdir(exist_ok=True)
    converted = 0

    for entry in LOGOS:
        svg_path = LOGOS_DIR / entry["svg"]
        png_path = LOGOS_DIR / entry["png"]

        if not svg_path.exists():
            print(f"[logos] SVG not found, skipping: {svg_path}")
            continue

        print(f"[logos] Converting {svg_path.name} → {png_path.name} ...")

        ok = (svg_to_png_cairosvg(svg_path, png_path, args.height) or
              svg_to_png_inkscape(svg_path, png_path, args.height) or
              fallback_text_logo(entry["svg"].split("_")[0], png_path, args.height))

        if ok:
            print(f"[logos] Saved: {png_path}")
            converted += 1
        else:
            print(f"[logos] WARNING: Could not convert {svg_path.name}", file=sys.stderr)

    print(f"[logos] Done. {converted}/{len(LOGOS)} logos converted.")


if __name__ == "__main__":
    main()
