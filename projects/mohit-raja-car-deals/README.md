# Mohit & Raja Car Deals — Sample Website

Single-file demo site for a Chandigarh-based luxury pre-owned car showroom, built with the `ui-ux-pro-max` skill (Trust & Authority style cues, Automotive/Luxury color system, Playfair Display + Inter typography, GSAP scroll/reveal motion).

Open `index.html` directly in a browser — no build step required.

## What's included

- Animated hero: the featured Lexus LX 570 photo assembles from puzzle-piece shards on load (GSAP) and disassembles again as you scroll past, with a subtle mouse-parallax tilt.
- Full inventory grid of all 42 cars from the current stock list, each with brand/year badges, an "estimated price" tag (from the given "demand" prices), spec tags, and a detail modal with a WhatsApp enquiry link pre-filled with the car's name and price.
- Brand filter bar, animated scroll reveals, showroom photo gallery, "why us" trust section, and a contact section with all phone numbers, address and an embedded map.
- Logo cropped from the showroom signage photo (`assets/logo/mr-logo.png`).

## Known limitation: car photos

This sandboxed build environment's network policy blocks fetching images from third-party CDNs/dealer sites (only a small allowlist like npm/GitHub/S3 is reachable), so an automated per-model photo fetch for all 42 cars was not possible from here. Every car card gracefully falls back to a clean branded placeholder (brand name, model, accent color) when its photo file is missing, so the site is fully functional as-is.

Only one real photo was fetched successfully: `assets/cars/01.jpg` (Volvo S90 2019).

**To add the remaining real photos later** (once you have normal internet access, e.g. on your own machine or once the domain/hosting is set up): drop a JPG for each car at
```
assets/cars/01.jpg ... assets/cars/42.jpg
```
matching the car IDs in the `CARS` array inside `index.html` (search for `const CARS = [`). No code changes needed — the `<img>` tags already point at this naming convention and will pick up any file you add automatically.

## Next steps before going live

- Swap in real photos per the naming convention above (ideally matching each car's exact year/trim).
- Confirm/replace the placeholder Google Maps embed query with the exact pin once available.
- Once a domain is purchased, this can be deployed as-is (static HTML) or migrated into a framework via the `ui-ux-pro-max` skill's `--stack` option if a CMS/backend is needed later.
