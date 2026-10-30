#!/usr/bin/env python3
"""
qa_check.py  —  Contact-sheet generator + QR decode + PASS/FAIL checker.

For each PNG in out/ (or a supplied list), it:
  • Checks minimum dimensions (1080×900 for posters, 1080×1350+ for stories)
  • Checks file size > 50KB (empty / broken renders are tiny)
  • Tries to decode any QR code present (OpenCV optional)
  • Assembles a contact sheet (Pillow)
  • Prints PASS / FAIL per image and exits with code 1 if any fail

Usage:
    python qa_check.py                    # checks out/*.png
    python qa_check.py out/festival_*.png
    python qa_check.py --sheet out/qa_sheet.png
"""
import argparse
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
MIN_SIZE_BYTES = 50_000   # 50 KB


def check_image(img_path: Path) -> dict:
    result = {"file": str(img_path), "ok": True, "issues": [], "dims": None, "qr": None}

    if not img_path.exists():
        result["ok"] = False
        result["issues"].append("FILE_NOT_FOUND")
        return result

    size_bytes = img_path.stat().st_size
    if size_bytes < MIN_SIZE_BYTES:
        result["ok"] = False
        result["issues"].append(f"TOO_SMALL ({size_bytes} bytes < {MIN_SIZE_BYTES})")

    try:
        from PIL import Image
        img = Image.open(img_path)
        w, h = img.size
        result["dims"] = (w, h)

        # Dimension checks
        name = img_path.stem.lower()
        if "story" in name or "reel" in name or "kc" in name:
            if w < 1080 or h < 1350:
                result["ok"] = False
                result["issues"].append(f"DIMS_TOO_SMALL ({w}×{h}, need ≥1080×1350)")
        elif "cv" in name or "cover" in name:
            if w < 1080 or h < 540:
                result["ok"] = False
                result["issues"].append(f"DIMS_TOO_SMALL ({w}×{h})")
        elif "pp" in name or "profile" in name:
            if w < 360 or h < 360:
                result["ok"] = False
                result["issues"].append(f"DIMS_TOO_SMALL ({w}×{h})")
        else:
            if w < 1080 or h < 900:
                result["ok"] = False
                result["issues"].append(f"DIMS_TOO_SMALL ({w}×{h}, need ≥1080×900)")

    except ImportError:
        result["issues"].append("PILLOW_NOT_INSTALLED (dimension check skipped)")
    except Exception as e:
        result["ok"] = False
        result["issues"].append(f"READ_ERROR: {e}")

    # QR decode (optional — needs opencv-python)
    try:
        import cv2
        import numpy as np
        from PIL import Image as PILImage

        cv_img = cv2.imread(str(img_path))
        if cv_img is not None:
            detector = cv2.QRCodeDetector()
            data, bbox, _ = detector.detectAndDecode(cv_img)
            if data:
                result["qr"] = data
    except ImportError:
        pass
    except Exception:
        pass

    return result


def make_contact_sheet(results: list, out_path: Path, cols: int = 4):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("[qa] Pillow not installed — skipping contact sheet.", file=sys.stderr)
        return

    thumb_w, thumb_h = 320, 320
    padding = 10
    label_h = 40

    valid = [r for r in results if r.get("dims")]
    if not valid:
        return

    rows = (len(valid) + cols - 1) // cols
    sheet_w = cols * (thumb_w + padding) + padding
    sheet_h = rows * (thumb_h + label_h + padding) + padding

    sheet = Image.new("RGB", (sheet_w, sheet_h), (30, 30, 30))
    draw  = ImageDraw.Draw(sheet)

    for i, r in enumerate(valid):
        col = i % cols
        row = i // cols
        x = padding + col * (thumb_w + padding)
        y = padding + row * (thumb_h + label_h + padding)

        try:
            img = Image.open(r["file"]).convert("RGB")
            img.thumbnail((thumb_w, thumb_h), Image.LANCZOS)
            # Centre on thumb area
            tx = x + (thumb_w - img.width) // 2
            ty = y + (thumb_h - img.height) // 2
            sheet.paste(img, (tx, ty))
        except Exception:
            draw.rectangle([x, y, x+thumb_w, y+thumb_h], fill=(50, 50, 50))

        color = (60, 200, 80) if r["ok"] else (220, 60, 60)
        label = "PASS" if r["ok"] else "FAIL"
        name  = Path(r["file"]).name[:28]
        draw.rectangle([x, y+thumb_h, x+thumb_w, y+thumb_h+label_h], fill=color)
        draw.text((x+6, y+thumb_h+8), f"{label}  {name}", fill=(255,255,255))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(str(out_path))
    print(f"[qa] Contact sheet: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="QA check for rendered creatives.")
    parser.add_argument("files",  nargs="*", help="PNG files to check (default: out/*.png)")
    parser.add_argument("--sheet", default="out/qa_sheet.png", help="Contact sheet output path")
    parser.add_argument("--json-out", help="Write JSON results to this file")
    args = parser.parse_args()

    if args.files:
        paths = [Path(f) for f in args.files]
    else:
        out_dir = SCRIPT_DIR / "out"
        paths = sorted(out_dir.glob("*.png"))

    if not paths:
        print("[qa] No PNG files found.", file=sys.stderr)
        sys.exit(0)

    results = []
    for p in paths:
        r = check_image(p)
        results.append(r)
        status = "PASS" if r["ok"] else "FAIL"
        dims   = f"  {r['dims'][0]}×{r['dims'][1]}" if r["dims"] else ""
        qr     = f"  QR={r['qr']}" if r["qr"] else ""
        issues = f"  !! {', '.join(r['issues'])}" if r["issues"] else ""
        print(f"  [{status}] {Path(r['file']).name}{dims}{qr}{issues}")

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(results, indent=2))

    sheet_path = Path(args.sheet)
    if not sheet_path.is_absolute():
        sheet_path = SCRIPT_DIR / sheet_path
    make_contact_sheet(results, sheet_path)

    passed = sum(1 for r in results if r["ok"])
    failed = len(results) - passed
    print(f"\n[qa] {passed} PASS  {failed} FAIL  (total {len(results)})")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
