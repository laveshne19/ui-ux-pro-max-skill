#!/usr/bin/env python3
"""
make_festival.py  —  Multi-brand festival greeting generator.

Usage:
    python make_festival.py karwa_chauth          # all 3 brands
    python make_festival.py diwali --brand nalanda
    python make_festival.py holi --brand bizwrap --out out/holi_bw.png
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
BRANDS_FILE = SCRIPT_DIR / "brands.json"
RENDER_JS   = SCRIPT_DIR / "render.js"
TEMPLATE    = str(SCRIPT_DIR / "templates" / "festival_greeting" / "kc.html")

FESTIVALS = {
    "diwali":        {"motif": "diya",     "title": "Happy Diwali!", "subtitle": "Shubh Deepawali", "sky": ["#1a0a2e","#2d1055","#4a0e8f"], "date_label": "Diwali"},
    "karwa_chauth":  {"motif": "moon",     "title": "Karwa Chauth Mubarak", "subtitle": "करवा चौथ की शुभकामनाएँ", "sky": ["#0d1b3e","#1e3a6e","#0a2550"], "date_label": "Karwa Chauth"},
    "gurpurab":      {"motif": "light",    "title": "Gurpurab Mubarak", "subtitle": "ਗੁਰਪੁਰਬ ਦੀਆਂ ਵਧਾਈਆਂ", "sky": ["#0a1a35","#1a3055","#0d2040"], "date_label": "Gurpurab"},
    "holi":          {"motif": "rangoli",  "title": "Happy Holi!", "subtitle": "होली की हार्दिक शुभकामनाएँ", "sky": ["#1a0a1a","#3d1055","#1a0a3e"], "date_label": "Holi"},
    "rakhi":         {"motif": "rakhi",    "title": "Happy Raksha Bandhan", "subtitle": "रक्षाबंधन की शुभकामनाएँ", "sky": ["#1a0d2e","#2d1850","#0d1030"], "date_label": "Raksha Bandhan"},
    "lohri":         {"motif": "fire",     "title": "Happy Lohri!", "subtitle": "ਲੋਹੜੀ ਦੀਆਂ ਲੱਖ ਲੱਖ ਵਧਾਈਆਂ", "sky": ["#0d0800","#1a1000","#0a0600"], "date_label": "Lohri"},
    "new_year":      {"motif": "firework", "title": "Happy New Year!", "subtitle": "नव वर्ष की हार्दिक शुभकामनाएँ", "sky": ["#020510","#050d20","#030810"], "date_label": "New Year"},
    "independence":  {"motif": "flag",     "title": "Happy Independence Day", "subtitle": "स्वतंत्रता दिवस की शुभकामनाएँ", "sky": ["#010810","#021530","#010c20"], "date_label": "Independence Day"},
}

ALL_BRANDS = ["nalanda", "bizwrap", "cgi"]


def run_render(render_cfg: dict, brand_id: str, out_file: Path, retries: int = 3) -> bool:
    cmd = [
        "node", str(RENDER_JS),
        "festival",
        json.dumps(render_cfg),
        brand_id,
        str(out_file),
    ]
    delays = [1, 2, 3]
    for attempt in range(retries):
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(SCRIPT_DIR))
        if result.returncode == 0:
            return True
        print(f"[festival] Render attempt {attempt+1} failed: {result.stderr.strip()}", file=sys.stderr)
        if attempt < retries - 1:
            time.sleep(delays[attempt])
    return False


def make_one(festival_key: str, brand_id: str, out_path: Path, date_str: str = "") -> bool:
    if not BRANDS_FILE.exists():
        print(f"[festival] ERROR: brands.json not found.", file=sys.stderr)
        return False
    brands = json.loads(BRANDS_FILE.read_text())
    brand = brands.get(brand_id)
    if not brand:
        print(f"[festival] ERROR: Unknown brand '{brand_id}'.", file=sys.stderr)
        return False

    meta = FESTIVALS.get(festival_key)
    if not meta:
        print(f"[festival] ERROR: Unknown festival '{festival_key}'. Available: {list(FESTIVALS)}", file=sys.stderr)
        return False

    render_cfg = {
        "festival": festival_key,
        "motif":    meta["motif"],
        "title":    meta["title"],
        "subtitle": meta["subtitle"],
        "sky":      meta["sky"],
        "date":     date_str or meta["date_label"],
    }

    print(f"[festival] Rendering {meta['title']} — brand={brand_id} → {out_path}")
    ok = run_render(render_cfg, brand_id, out_path)
    if ok:
        print(f"[festival] Saved: {out_path}")
    else:
        print(f"[festival] ERROR: Failed to render for brand={brand_id}.", file=sys.stderr)
    return ok


def main():
    parser = argparse.ArgumentParser(description="Generate festival greeting images.")
    parser.add_argument("festival", help=f"Festival key: {', '.join(FESTIVALS)}")
    parser.add_argument("--brand",  help="Brand ID (default: all brands)")
    parser.add_argument("--out",    help="Output file (single brand only)")
    parser.add_argument("--date",   default="", help="Date label on the greeting")
    args = parser.parse_args()

    festival_key = args.festival.lower().replace(" ", "_").replace("-", "_")
    if festival_key not in FESTIVALS:
        close = [k for k in FESTIVALS if k.startswith(festival_key[:4])]
        hint  = f"  Did you mean: {close}" if close else ""
        print(f"[festival] ERROR: Unknown festival '{festival_key}'.{hint}", file=sys.stderr)
        print(f"[festival] Available: {', '.join(FESTIVALS)}", file=sys.stderr)
        sys.exit(1)

    if not RENDER_JS.exists():
        print(f"[festival] ERROR: render.js not found at {RENDER_JS}", file=sys.stderr)
        sys.exit(1)

    out_dir = SCRIPT_DIR / "out"
    out_dir.mkdir(exist_ok=True)

    brands_to_render = [args.brand] if args.brand else ALL_BRANDS

    errors = 0
    for brand_id in brands_to_render:
        if args.out and len(brands_to_render) == 1:
            out_path = Path(args.out)
        else:
            out_path = out_dir / f"festival_{festival_key}_{brand_id}.png"

        ok = make_one(festival_key, brand_id, out_path, args.date)
        if not ok:
            errors += 1

    if errors:
        print(f"[festival] {errors} render(s) failed.", file=sys.stderr)
        sys.exit(1)
    print(f"[festival] Done. {len(brands_to_render)} image(s) saved to {out_dir}/")


if __name__ == "__main__":
    main()
