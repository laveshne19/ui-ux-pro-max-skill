# Nalanda Creatives — Banner, Poster & Reel Pipeline

Automated creative production for **Nalanda Enterprises**, **BizWrap India** and **Corporate Gifting India**.

---

## Quick Start

```bash
cd creatives
npm install                          # install Playwright
node render.js gbp_post '{}' nalanda out/test.png   # smoke test
```

---

## Directory Layout

```
creatives/
├── brands.json                  Brand presets (colours, fonts, logos)
├── render.js                    Playwright renderer (all templates)
├── fetch_product.py             Shopify product fetcher + background removal
├── make_scheme.py               "Buy X Get Y Free" poster from YAML
├── make_festival.py             Multi-brand festival greeting generator
├── make_reel.py                 Full reel pipeline (voice + music + video)
├── synth.py                     D-major original backing track generator
├── qa_check.py                  Contact sheet + QR decode + PASS/FAIL
├── gen_logos.py                 SVG → PNG logo converter
├── batch.yaml                   Example Diwali campaign
├── package.json
├── logos/                       SVG/PNG brand logos
├── img/                         Product cut-outs (index.json)
├── fonts/                       Optional local fonts
├── templates/
│   ├── gbp_post/
│   │   ├── p.html               1200×900 GBP/poster
│   │   ├── pp.html              720×720 profile picture
│   │   └── cv.html              1920×1080 cover banner
│   ├── festival_greeting/
│   │   └── kc.html              1080×1350 festival greeting
│   └── studio_reel/
│       └── v.html               1080×1920 studio product reel
└── out/                         Output images & videos
```

---

## Scripts

### `render.js` — Unified renderer

```bash
node render.js <template> '<json-config>' <brand-id> <output.png>
```

| Template | Dimensions | Description |
|----------|-----------|-------------|
| `gbp_post` | 1200×900 | GBP/Instagram poster |
| `profile` | 720×720 | Profile picture |
| `cover` | 1920×1080 | Cover banner |
| `festival` | 1080×1350 | Festival greeting |
| `reel` | 1080×1920 | Studio product reel frame |

**Brand IDs:** `nalanda` · `bizwrap` · `cgi`

---

### `fetch_product.py` — Product image fetcher

Downloads product images from Shopify and removes the background.

```bash
python fetch_product.py "boAt Rockerz 550"
python fetch_product.py "Zebronics Zeb-County" --force
python fetch_product.py "boAt Airdopes 141" --store boat --no-bg-remove
```

Images are saved to `img/<slug>_c.png` and indexed in `img/index.json`.

**Background removal algorithm:**
Flood-fill border-connected pixels within colour distance 22 of the border median → Gaussian feather σ=1.1 → zero 4px border → drop components < 0.4% of image area.

---

### `make_scheme.py` — Scheme poster

```bash
python make_scheme.py batch.yaml
python make_scheme.py my_offer.yaml --brand bizwrap --out out/offer_bw.png
```

**YAML fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `brand` | Yes | Brand ID |
| `headline` | Yes | Poster headline (HTML `<em>` for gold) |
| `kick` | No | Kicker line above headline |
| `sub` | No | Subheading / body copy |
| `chips` | No | List of pill badges |
| `badge` | No | Top-right badge label |
| `price` | No | Price (only shown if provided) |
| `images` | No | List of product image paths |

---

### `make_festival.py` — Festival greetings

```bash
python make_festival.py diwali                    # all 3 brands
python make_festival.py karwa_chauth --brand nalanda
python make_festival.py holi --brand cgi --out out/holi_cgi.png
```

**Supported festivals:** `diwali` · `karwa_chauth` · `gurpurab` · `holi` · `rakhi` · `lohri` · `new_year` · `independence`

---

### `make_reel.py` — Product reel video

```bash
# Uses products from img/index.json automatically
python make_reel.py --brand nalanda --out out/reel_ne.mp4

# Supply products directly
python make_reel.py --brand bizwrap \
  --products '[{"title":"boAt Rockerz 550","images":["img/boat_rockerz_550_c.png"]}]'
```

**Pipeline:**
1. Script from product titles → edge-tts voice-over (en-IN-NeerjaNeural)
2. D-major backing track via `synth.py`
3. One frame per product via `render.js` (studio_reel template)
4. FFmpeg audio mix: voice + music (atempo=1.06, sidechain, loudnorm I=−14:TP=−1.5:LRA=11)
5. H.264 CRF 18 yuv420p 1080×1920 + AAC 256k

**Dependencies:**
```bash
pip install edge-tts pillow scipy numpy
# ffmpeg must be on PATH
```

---

### `synth.py` — Backing track generator

Generates an original D-major chord progression with kick, hi-hat and chime melody.
No samples, no copyrighted audio.

```bash
python synth.py --duration 30 --bpm 96 --out out/backing.wav
```

---

### `qa_check.py` — Quality assurance

```bash
python qa_check.py                         # checks out/*.png
python qa_check.py out/festival_*.png
python qa_check.py --sheet out/qa_sheet.png
```

Checks: file size > 50 KB, minimum dimensions per type, optional QR decode.
Exits with code 1 if any image fails.

---

### `gen_logos.py` — Logo converter

```bash
python gen_logos.py              # converts logos/*.svg → logos/*.png
python gen_logos.py --height 200
```

Requires: `cairosvg` (pip) **or** `inkscape`/`rsvg-convert` (system) **or** `Pillow` (fallback).

---

## Batch Campaign Example

```bash
# 1. Fetch product images
python fetch_product.py "boAt Rockerz 550"
python fetch_product.py "boAt Airdopes 141"
python fetch_product.py "Zebronics Zeb-County"

# 2. Diwali festival greetings for all brands
python make_festival.py diwali --date "2 November 2024"

# 3. Scheme poster for Nalanda
python make_scheme.py batch.yaml

# 4. Reels
python make_reel.py --brand nalanda

# 5. QA
python qa_check.py --sheet out/qa_sheet.png
```

---

## Brand Configuration (`brands.json`)

Each brand entry contains:

| Key | Description |
|-----|-------------|
| `id` | Brand identifier |
| `name` | Full brand name |
| `tagline` | One-line tagline |
| `logo` | Relative path to PNG logo |
| `logoHtml` | `<img>` tag HTML (with onerror fallback) |
| `primary` | Primary/dark colour |
| `accent` | Accent/gold colour |
| `light` | Light background colour |
| `dark` | Dark background colour |
| `website` | Website URL |
| `footer` | List of footer labels |
| `fontHeading` | Google Font name for headings |
| `fontBody` | Google Font name for body |

---

## Rules

- **No prices** unless explicitly provided in config/YAML.
- **No invented claims** — only text from config.
- **No copyrighted music** — `synth.py` generates original music only.
- **No fake presenters** — voice-over reads product/brand names only.
- **Never publish** output anywhere without the client's approval.

---

## Dependencies

| Tool | Purpose |
|------|---------|
| Node.js ≥ 18 + Playwright | Headless rendering |
| Python 3.x | All scripts |
| ffmpeg | Audio/video encoding (make_reel) |
| edge-tts | Voice-over synthesis |
| Pillow | Image processing, QA sheet |
| scipy, numpy | synth.py audio synthesis |
| cairosvg *(optional)* | SVG → PNG logo conversion |
| opencv-python *(optional)* | QR code detection in QA |
