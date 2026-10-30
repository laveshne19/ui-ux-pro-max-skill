#!/usr/bin/env python3
"""
make_scheme.py  —  Generate "Buy X Get Y Free" poster from a YAML config.

Usage:
    python make_scheme.py scheme.yaml
    python make_scheme.py scheme.yaml --brand bizwrap --out out/scheme_bw.png
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


def load_yaml(path: Path) -> dict:
    try:
        import yaml
        with open(path) as f:
            return yaml.safe_load(f)
    except ImportError:
        # Minimal YAML subset parser (key: value, lists with -)
        import re
        data = {}
        current_key = None
        current_list = None
        for raw_line in path.read_text().splitlines():
            line = raw_line.rstrip()
            if not line or line.lstrip().startswith('#'):
                continue
            if line.startswith('  - ') or line.startswith('- '):
                item = line.lstrip('- ').strip()
                if current_list is not None:
                    current_list.append(item)
                continue
            m = re.match(r'^(\w[\w_-]*):\s*(.*)', line)
            if m:
                key, val = m.group(1), m.group(2).strip()
                if val == '':
                    current_list = []
                    data[key] = current_list
                    current_key = key
                else:
                    val = val.strip('"\'')
                    data[key] = val
                    current_list = None
                    current_key = key
        return data


def validate_scheme(cfg: dict):
    required = ["brand", "headline"]
    missing = [k for k in required if not cfg.get(k)]
    if missing:
        print(f"[scheme] ERROR: YAML missing required fields: {missing}", file=sys.stderr)
        sys.exit(1)
    # No prices unless explicitly given
    if cfg.get("price") and not str(cfg["price"]).strip():
        del cfg["price"]


def build_render_config(cfg: dict, brand: dict) -> dict:
    """Translate scheme YAML → gbp_post render config."""
    chips = list(cfg.get("chips", []))
    if not chips and cfg.get("free_item"):
        chips = [f"FREE: {cfg['free_item']}"]

    items = []
    for img_entry in cfg.get("images", []):
        if isinstance(img_entry, str):
            items.append([img_entry, 480, 540, 760, 820])
        elif isinstance(img_entry, (list, tuple)):
            items.append(list(img_entry))

    render_cfg = {
        "kick":  cfg.get("kick", brand.get("tagline", "")),
        "hd":    cfg.get("headline", ""),
        "sub":   cfg.get("sub", ""),
        "chips": chips,
        "items": items,
        "stamp": [
            cfg.get("stamp_line1", ""),
            cfg.get("stamp_line2", ""),
        ],
    }

    if cfg.get("badge"):
        render_cfg["badge"] = cfg["badge"]

    if cfg.get("price"):
        render_cfg["hd"] = render_cfg["hd"] + f" · ₹{cfg['price']}"

    return render_cfg


def run_render(template: str, config: dict, brand_id: str, out_file: Path, retries: int = 3):
    cmd = [
        "node", str(RENDER_JS),
        template,
        json.dumps(config),
        brand_id,
        str(out_file),
    ]
    delays = [1, 2, 3]
    for attempt in range(retries):
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(SCRIPT_DIR))
        if result.returncode == 0:
            return True
        print(f"[render] Attempt {attempt+1} failed: {result.stderr.strip()}", file=sys.stderr)
        if attempt < retries - 1:
            time.sleep(delays[attempt])
    return False


def main():
    parser = argparse.ArgumentParser(description="Generate scheme poster from YAML.")
    parser.add_argument("yaml_file", help="Path to scheme YAML file")
    parser.add_argument("--brand",  help="Override brand ID from YAML")
    parser.add_argument("--out",    help="Output file path (default: out/<slug>.png)")
    args = parser.parse_args()

    yaml_path = Path(args.yaml_file)
    if not yaml_path.exists():
        print(f"[scheme] ERROR: YAML file not found: {yaml_path}", file=sys.stderr)
        sys.exit(1)

    cfg = load_yaml(yaml_path)
    validate_scheme(cfg)

    brand_id = args.brand or cfg.get("brand", "nalanda")

    if not BRANDS_FILE.exists():
        print(f"[scheme] ERROR: brands.json not found at {BRANDS_FILE}", file=sys.stderr)
        sys.exit(1)
    brands = json.loads(BRANDS_FILE.read_text())
    brand = brands.get(brand_id)
    if not brand:
        print(f"[scheme] ERROR: Unknown brand '{brand_id}'. Available: {list(brands.keys())}", file=sys.stderr)
        sys.exit(1)

    out_dir = SCRIPT_DIR / "out"
    out_dir.mkdir(exist_ok=True)

    slug = yaml_path.stem.replace(" ", "_").lower()
    out_file = Path(args.out) if args.out else out_dir / f"scheme_{brand_id}_{slug}.png"

    render_cfg = build_render_config(cfg, brand)

    print(f"[scheme] Rendering poster for brand={brand_id}, scheme={slug}")
    print(f"[scheme] Headline: {render_cfg['hd']}")

    if not RENDER_JS.exists():
        print(f"[scheme] ERROR: render.js not found at {RENDER_JS}", file=sys.stderr)
        sys.exit(1)

    ok = run_render("gbp_post", render_cfg, brand_id, out_file)
    if ok:
        print(f"[scheme] Saved: {out_file}")
    else:
        print(f"[scheme] ERROR: Render failed after retries.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
