#!/usr/bin/env python3
"""
fetch_product.py  —  Download and background-remove a product image from Shopify stores.

Usage:
    python fetch_product.py "boAt Rockerz 550"
    python fetch_product.py "Zebronics Zeb-County" --force
    python fetch_product.py "boAt Airdopes 141" --store boat
"""
import argparse
import json
import math
import os
import re
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# ── Store registry ────────────────────────────────────────────────────────────
STORES = {
    "boat":      {"host": "www.boat-lifestyle.com", "prefixes": ["boat", "rockerz", "airdopes", "bassheads", "stone", "nirvana"]},
    "zebronics": {"host": "zebronics.com",           "prefixes": ["zebronics", "zeb-"]},
    "vaku":      {"host": "vaku.in",                 "prefixes": ["vaku"]},
    "wiwu":      {"host": "www.wiwu.com",            "prefixes": ["wiwu"]},
}

# ── Background removal ────────────────────────────────────────────────────────
def _flood_fill_border_mask(arr):
    """Return a boolean mask of border-connected near-white pixels."""
    try:
        import numpy as np
    except ImportError:
        return None

    h, w = arr.shape[:2]
    visited = np.zeros((h, w), dtype=bool)
    queue = []

    # Seed from all 4 edges
    for y in range(h):
        for x in [0, w - 1]:
            if not visited[y, x]:
                visited[y, x] = True
                queue.append((y, x))
    for x in range(w):
        for y in [0, h - 1]:
            if not visited[y, x]:
                visited[y, x] = True
                queue.append((y, x))

    # BFS — keep only pixels within distance 22 of border median
    border_pixels = arr[0, :, :3].astype(float)
    border_pixels = np.vstack([border_pixels, arr[-1, :, :3].astype(float),
                                arr[:, 0, :3].astype(float), arr[:, -1, :3].astype(float)])
    median_color = np.median(border_pixels, axis=0)
    DIST_THRESH = 22.0

    bg_mask = np.zeros((h, w), dtype=bool)
    head = 0
    while head < len(queue):
        y, x = queue[head]; head += 1
        pix = arr[y, x, :3].astype(float)
        dist = np.linalg.norm(pix - median_color)
        if dist > DIST_THRESH:
            continue
        bg_mask[y, x] = True
        for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]:
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx]:
                visited[ny, nx] = True
                queue.append((ny, nx))

    return bg_mask


def remove_background(img_path: Path, out_path: Path):
    """Flood-fill border background removal with Gaussian feather."""
    try:
        from PIL import Image, ImageFilter
        import numpy as np
        from scipy.ndimage import label as scipy_label
    except ImportError as e:
        print(f"[bg] Missing dependency ({e}). Saving without bg removal.", file=sys.stderr)
        img_path.rename(out_path) if img_path != out_path else None
        return

    img = Image.open(img_path).convert("RGBA")
    arr = np.array(img)
    h, w = arr.shape[:2]

    bg_mask = _flood_fill_border_mask(arr)
    if bg_mask is None:
        img_path.rename(out_path) if img_path != out_path else None
        return

    # Feather with Gaussian σ=1.1
    from scipy.ndimage import gaussian_filter
    feathered = gaussian_filter(bg_mask.astype(float), sigma=1.1)
    alpha = np.clip((1.0 - feathered) * 255, 0, 255).astype(np.uint8)

    # Zero a 4px border
    alpha[:4, :] = 0; alpha[-4:, :] = 0
    alpha[:, :4] = 0; alpha[:, -4:] = 0

    # Keep only components > 0.4% of image
    inv_bg = (~bg_mask).astype(np.uint8)
    labeled, n_labels = scipy_label(inv_bg)
    total = h * w
    for lbl in range(1, n_labels + 1):
        comp = (labeled == lbl)
        if comp.sum() < total * 0.004:
            alpha[comp] = 0

    out_arr = arr.copy()
    out_arr[:, :, 3] = alpha

    result = Image.fromarray(out_arr, "RGBA")

    # Crop to content
    bbox = result.getbbox()
    if bbox:
        result = result.crop(bbox)

    result.save(str(out_path), "PNG")
    if img_path != out_path and img_path.exists():
        img_path.unlink()

    print(f"[bg] Saved cut-out: {out_path}")


# ── Network helpers ───────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Nalanda-Creatives/1.0)",
    "Accept": "application/json, */*",
}


def http_get(url: str, retries: int = 3):
    delays = [2, 4, 8]
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                return None  # not found — caller handles
            print(f"[net] HTTP {e.code} on {url} (attempt {attempt+1}/{retries})", file=sys.stderr)
        except Exception as e:
            print(f"[net] Error on {url}: {e} (attempt {attempt+1}/{retries})", file=sys.stderr)
        if attempt < retries - 1:
            time.sleep(delays[attempt])
    return None


def download_file(url: str, dest: Path, retries: int = 3):
    delays = [2, 4, 8]
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                dest.write_bytes(resp.read())
            return True
        except Exception as e:
            print(f"[net] Download failed: {e} (attempt {attempt+1}/{retries})", file=sys.stderr)
        if attempt < retries - 1:
            time.sleep(delays[attempt])
    return False


# ── Shopify helpers ───────────────────────────────────────────────────────────
def shopify_search(host: str, query: str):
    q = urllib.parse.quote(query)
    url = f"https://{host}/search/suggest.json?q={q}&resources[type]=product&resources[limit]=3"
    data = http_get(url)
    if not data:
        return []
    try:
        obj = json.loads(data)
        products = obj.get("resources", {}).get("results", {}).get("products", [])
        return products
    except Exception:
        return []


def shopify_product(host: str, handle: str):
    url = f"https://{host}/products/{handle}.js"
    data = http_get(url)
    if not data:
        return None
    try:
        return json.loads(data)
    except Exception:
        return None


def clean_image_url(url: str, width: int = 1400) -> str:
    """Strip existing Shopify size params and add ?width=<width>."""
    url = re.sub(r'\?.*$', '', url)
    url = re.sub(r'_\d+x\d*(\.[a-z]+)$', r'\1', url, flags=re.IGNORECASE)
    url = re.sub(r'_\d+x(\.[a-z]+)$',   r'\1', url, flags=re.IGNORECASE)
    return f"{url}?width={width}"


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9]+', '_', text)
    return text.strip('_')


# ── Main ──────────────────────────────────────────────────────────────────────
def detect_store(query: str):
    q = query.lower()
    for key, meta in STORES.items():
        for prefix in meta["prefixes"]:
            if q.startswith(prefix):
                return key
    return None


def update_index(index_path: Path, entry: dict):
    entries = []
    if index_path.exists():
        try:
            entries = json.loads(index_path.read_text())
        except Exception:
            entries = []
    # Remove existing entry for same slug
    entries = [e for e in entries if e.get("slug") != entry["slug"]]
    entries.append(entry)
    index_path.write_text(json.dumps(entries, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="Fetch and cut out product images from Shopify stores.")
    parser.add_argument("query",  help='Product name, e.g. "boAt Rockerz 550"')
    parser.add_argument("--store", help="Force store key (boat|zebronics|vaku|wiwu)")
    parser.add_argument("--force", action="store_true", help="Re-download even if image exists")
    parser.add_argument("--no-bg-remove", action="store_true", help="Skip background removal")
    parser.add_argument("--img-dir", default="img", help="Directory for output images (default: img)")
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    img_dir    = script_dir / args.img_dir
    img_dir.mkdir(exist_ok=True)
    index_path = img_dir / "index.json"

    query = args.query.strip()

    # Detect store
    store_key = args.store or detect_store(query)
    if store_key:
        candidates = [store_key]
    else:
        candidates = list(STORES.keys())

    found_products = []
    for key in candidates:
        host = STORES[key]["host"]
        print(f"[fetch] Searching {host} for: {query}")
        products = shopify_search(host, query)
        if products:
            found_products = [(key, host, p) for p in products]
            print(f"[fetch] Found {len(products)} result(s) on {host}")
            break

    if not found_products:
        print(f"[fetch] ERROR: No product found for '{query}' on any store. Not substituting.", file=sys.stderr)
        sys.exit(1)

    store_key, host, product_meta = found_products[0]
    handle = product_meta.get("handle", "")
    if not handle:
        print("[fetch] ERROR: Product handle missing.", file=sys.stderr)
        sys.exit(1)

    print(f"[fetch] Fetching product: {handle}")
    product = shopify_product(host, handle)
    if not product:
        print(f"[fetch] ERROR: Could not fetch product details for '{handle}'.", file=sys.stderr)
        sys.exit(1)

    title = product.get("title", handle)
    slug  = slugify(title)

    # Collect images
    images = product.get("images", [])
    if not images:
        print("[fetch] ERROR: Product has no images.", file=sys.stderr)
        sys.exit(1)

    saved = []
    for i, img_data in enumerate(images[:2]):
        img_url = img_data.get("src", "") if isinstance(img_data, dict) else str(img_data)
        img_url = clean_image_url(img_url)

        suffix   = "" if i == 0 else f"_{i+1}"
        raw_path = img_dir / f"{slug}{suffix}_raw.jpg"
        out_path = img_dir / f"{slug}{suffix}_c.png"

        if out_path.exists() and not args.force:
            print(f"[fetch] Already exists (use --force to re-download): {out_path}")
            saved.append(str(out_path))
            continue

        print(f"[fetch] Downloading image {i+1}: {img_url}")
        if not download_file(img_url, raw_path):
            print(f"[fetch] WARNING: Failed to download image {i+1}.", file=sys.stderr)
            continue

        if args.no_bg_remove:
            raw_path.rename(out_path)
        else:
            remove_background(raw_path, out_path)

        saved.append(str(out_path))

    if not saved:
        print("[fetch] ERROR: No images saved.", file=sys.stderr)
        sys.exit(1)

    # Update index
    entry = {
        "slug":       slug,
        "title":      title,
        "url":        f"https://{host}/products/{handle}",
        "source":     store_key,
        "images":     saved,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    update_index(index_path, entry)
    print(f"[fetch] Index updated: {index_path}")
    print(f"[fetch] Done. Slug: {slug}")
    for p in saved:
        print(f"  -> {p}")


if __name__ == "__main__":
    main()
