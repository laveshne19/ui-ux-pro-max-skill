#!/usr/bin/env python3
"""
make_reel.py  —  Full reel pipeline: voice-over + music + frame rendering + FFmpeg encode.

Pipeline:
  1. Load products from img/index.json (or --products JSON)
  2. Synthesise voice-over with edge-tts (en-IN-NeerjaNeural)
  3. Generate backing music with synth.py
  4. Render one frame per product shot via render.js (studio_reel template)
  5. Mix audio: voice + music with FFmpeg
  6. Encode final reel: libx264 CRF 18 yuv420p 1080x1920 + AAC 256k

Usage:
    python make_reel.py --brand nalanda --out out/reel_ne.mp4
    python make_reel.py --brand bizwrap --products '[{"title":"boAt Rockerz 550","images":["img/boat_rockerz_550_c.png"]}]'
"""
import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
BRANDS_FILE = SCRIPT_DIR / "brands.json"
RENDER_JS   = SCRIPT_DIR / "render.js"
SYNTH_PY    = SCRIPT_DIR / "synth.py"


# ── Helpers ──────────────────────────────────────────────────────────────────

def check_ffmpeg():
    if not shutil.which("ffmpeg"):
        print("[reel] ERROR: ffmpeg not found. Install it and re-run.", file=sys.stderr)
        sys.exit(1)


def check_node():
    if not shutil.which("node"):
        print("[reel] ERROR: node not found.", file=sys.stderr)
        sys.exit(1)


def run(cmd: list, cwd: str = None, retries: int = 1, delays=None) -> subprocess.CompletedProcess:
    delays = delays or [2, 4, 8]
    for attempt in range(retries):
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd or str(SCRIPT_DIR))
        if result.returncode == 0:
            return result
        if attempt < retries - 1:
            print(f"[reel] Cmd failed (attempt {attempt+1}): {' '.join(cmd[:3])} ...", file=sys.stderr)
            time.sleep(delays[min(attempt, len(delays)-1)])
        else:
            return result
    return result


# ── Voice-over ───────────────────────────────────────────────────────────────

def build_script(products: list, brand: dict) -> str:
    lines = [f"Welcome to {brand['name']}."]
    for p in products:
        title = p.get("title", "")
        if title:
            lines.append(f"{title}.")
    lines.append(f"Shop now at {brand.get('website', '')}.")
    return "  ".join(lines)


async def _tts(text: str, out_wav: Path):
    try:
        import edge_tts
    except ImportError:
        print("[reel] edge-tts not installed. Skipping voice-over.", file=sys.stderr)
        return False, []

    communicate = edge_tts.Communicate(text, "en-IN-NeerjaNeural")
    timings = []
    audio_data = []

    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data.append(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            timings.append({
                "word":   chunk.get("text", ""),
                "offset": chunk.get("offset", 0) / 10_000_000,
                "dur":    chunk.get("duration", 0) / 10_000_000,
            })

    if audio_data:
        out_wav.parent.mkdir(parents=True, exist_ok=True)
        out_wav.write_bytes(b"".join(audio_data))
        return True, timings
    return False, []


def generate_voiceover(text: str, out_wav: Path, tl_path: Path) -> bool:
    print(f"[reel] Generating voice-over ({len(text)} chars) ...")
    ok, timings = asyncio.run(_tts(text, out_wav))
    if ok:
        tl_path.write_text(json.dumps(timings, indent=2, ensure_ascii=False))
        print(f"[reel] Voice-over saved: {out_wav}  ({len(timings)} words)")
    return ok


# ── Music ─────────────────────────────────────────────────────────────────────

def generate_music(duration: float, out_wav: Path) -> bool:
    print(f"[reel] Synthesising backing music ({duration:.0f}s) ...")
    result = run([sys.executable, str(SYNTH_PY),
                  "--duration", str(duration + 2),
                  "--out", str(out_wav)])
    if result.returncode == 0:
        print(f"[reel] Music saved: {out_wav}")
        return True
    print(f"[reel] Music synthesis failed: {result.stderr.strip()}", file=sys.stderr)
    return False


# ── Frames ────────────────────────────────────────────────────────────────────

def render_frames(products: list, brand_id: str, frames_dir: Path) -> list:
    frames_dir.mkdir(parents=True, exist_ok=True)
    frame_paths = []

    for i, product in enumerate(products):
        images = product.get("images", [])
        title  = product.get("title", f"Product {i+1}")
        img1   = images[0] if images else ""

        shot_cfg = {
            "shots": [
                {"type": "stage", "img": img1, "caption": title, "subcaption": ""},
            ],
            "activeShot": 0,
        }
        if len(images) >= 2:
            shot_cfg["shots"].append({
                "type":  "full",
                "img":   images[1],
                "caption": title,
            })

        out_frame = frames_dir / f"frame_{i:03d}.png"
        cmd = [
            "node", str(RENDER_JS),
            "reel",
            json.dumps(shot_cfg),
            brand_id,
            str(out_frame),
        ]
        result = run(cmd, retries=3)
        if result.returncode == 0:
            frame_paths.append(str(out_frame))
            print(f"[reel] Frame {i+1}/{len(products)}: {out_frame.name}")
        else:
            print(f"[reel] WARNING: Frame {i+1} failed: {result.stderr.strip()}", file=sys.stderr)

    return frame_paths


# ── Audio mix ─────────────────────────────────────────────────────────────────

def mix_audio(voice_wav: Path, music_wav: Path, out_wav: Path, voice_ok: bool) -> bool:
    out_wav.parent.mkdir(parents=True, exist_ok=True)

    if not voice_ok or not voice_wav.exists():
        # Music only — loudnorm + tempo adjust
        cmd = [
            "ffmpeg", "-y",
            "-i", str(music_wav),
            "-filter:a", "atempo=1.06,loudnorm=I=-14:TP=-1.5:LRA=11",
            "-c:a", "aac", "-b:a", "256k",
            str(out_wav),
        ]
    else:
        # Voice + sidechain-compressed music
        cmd = [
            "ffmpeg", "-y",
            "-i", str(voice_wav),
            "-i", str(music_wav),
            "-filter_complex",
            "[1:a]atempo=1.06,volume=0.25,apad[bg];"
            "[0:a][bg]amix=inputs=2:duration=longest[mix];"
            "[mix]loudnorm=I=-14:TP=-1.5:LRA=11[out]",
            "-map", "[out]",
            "-c:a", "aac", "-b:a", "256k",
            str(out_wav),
        ]

    result = run(cmd)
    if result.returncode != 0:
        print(f"[reel] Audio mix failed: {result.stderr.strip()}", file=sys.stderr)
        return False
    print(f"[reel] Mixed audio: {out_wav}")
    return True


# ── Video encode ──────────────────────────────────────────────────────────────

def encode_video(frame_paths: list, audio_wav: Path, out_mp4: Path, fps: float = 0.5) -> bool:
    if not frame_paths:
        print("[reel] ERROR: No frames to encode.", file=sys.stderr)
        return False

    # Write concat list
    concat_txt = audio_wav.parent / "concat.txt"
    with open(concat_txt, "w") as f:
        for fp in frame_paths:
            hold = 1.0 / fps
            f.write(f"file '{fp}'\n")
            f.write(f"duration {hold:.2f}\n")
        # repeat last frame
        f.write(f"file '{frame_paths[-1]}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_txt),
        "-i", str(audio_wav),
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-c:a", "copy",
        "-shortest",
        str(out_mp4),
    ]
    result = run(cmd)
    if result.returncode != 0:
        print(f"[reel] Video encode failed: {result.stderr.strip()}", file=sys.stderr)
        return False
    print(f"[reel] Encoded: {out_mp4}")
    return True


# ── Main ──────────────────────────────────────────────────────────────────────

def load_products_from_index(limit: int = 5) -> list:
    index_path = SCRIPT_DIR / "img" / "index.json"
    if not index_path.exists():
        return []
    try:
        entries = json.loads(index_path.read_text())
        return entries[:limit]
    except Exception:
        return []


def main():
    parser = argparse.ArgumentParser(description="Generate product reel video.")
    parser.add_argument("--brand",    default="nalanda", help="Brand ID (default: nalanda)")
    parser.add_argument("--products", help="JSON array of product objects (overrides index.json)")
    parser.add_argument("--out",      help="Output MP4 path (default: out/reel_<brand>.mp4)")
    parser.add_argument("--fps",      type=float, default=0.4, help="Frames per second (default 0.4 = 2.5s/frame)")
    parser.add_argument("--limit",    type=int, default=5, help="Max products to include (default 5)")
    args = parser.parse_args()

    check_ffmpeg()
    check_node()

    if not BRANDS_FILE.exists():
        print("[reel] ERROR: brands.json not found.", file=sys.stderr)
        sys.exit(1)
    brands = json.loads(BRANDS_FILE.read_text())
    brand = brands.get(args.brand)
    if not brand:
        print(f"[reel] ERROR: Unknown brand '{args.brand}'.", file=sys.stderr)
        sys.exit(1)

    if args.products:
        try:
            products = json.loads(args.products)
        except Exception as e:
            print(f"[reel] ERROR: Invalid --products JSON: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        products = load_products_from_index(args.limit)

    if not products:
        print("[reel] ERROR: No products. Run fetch_product.py first or pass --products.", file=sys.stderr)
        sys.exit(1)

    products = products[:args.limit]
    print(f"[reel] {len(products)} product(s) — brand={args.brand}")

    out_dir = SCRIPT_DIR / "out"
    out_dir.mkdir(exist_ok=True)

    work_dir = out_dir / f"reel_work_{args.brand}"
    work_dir.mkdir(exist_ok=True)

    out_mp4 = Path(args.out) if args.out else out_dir / f"reel_{args.brand}.mp4"

    # Duration: 2.5s per frame + 1s tail
    duration = len(products) * (1.0 / args.fps) + 1.0

    # Voice-over
    script   = build_script(products, brand)
    vo_wav   = work_dir / "voiceover.mp3"
    tl_json  = work_dir / "tl.json"
    voice_ok = generate_voiceover(script, vo_wav, tl_json)

    # Music
    music_wav = work_dir / "music.wav"
    music_ok  = generate_music(duration, music_wav)
    if not music_ok:
        print("[reel] WARNING: Music generation failed — video will have no audio.", file=sys.stderr)

    # Frames
    frames_dir = work_dir / "frames"
    frame_paths = render_frames(products, args.brand, frames_dir)
    if not frame_paths:
        print("[reel] ERROR: No frames rendered. Check render.js + templates.", file=sys.stderr)
        sys.exit(1)

    # Mix audio
    mixed_wav = work_dir / "mixed.aac"
    audio_ok  = False
    if music_ok:
        audio_ok = mix_audio(vo_wav, music_wav, mixed_wav, voice_ok)

    # Encode
    audio_source = mixed_wav if audio_ok else (music_wav if music_ok else vo_wav if voice_ok else None)
    if audio_source and audio_source.exists():
        ok = encode_video(frame_paths, audio_source, out_mp4, args.fps)
    else:
        # Silent video fallback
        concat_txt = work_dir / "concat.txt"
        with open(concat_txt, "w") as f:
            for fp in frame_paths:
                f.write(f"file '{fp}'\n")
                f.write(f"duration {1.0/args.fps:.2f}\n")
            f.write(f"file '{frame_paths[-1]}'\n")
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_txt),
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(out_mp4),
        ]
        ok = run(cmd).returncode == 0
        if ok:
            print(f"[reel] Encoded (silent): {out_mp4}")

    if not ok:
        print("[reel] ERROR: Video encoding failed.", file=sys.stderr)
        sys.exit(1)

    print(f"\n[reel] Reel complete: {out_mp4}")


if __name__ == "__main__":
    main()
