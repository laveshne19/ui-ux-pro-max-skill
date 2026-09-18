# Mohit & Raja Car Deals — Sample Website

Single-file demo site for a Chandigarh-based luxury pre-owned car showroom, built with the `ui-ux-pro-max` skill and an Apple-inspired light design system (white/`#F5F5F7` panels, `-apple-system`/Inter typography, GSAP scroll/reveal motion), reviewed against Apple's Human Interface Guidelines for color, typography, layout and materials.

Open `index.html` directly in a browser — no build step required.

## What's included

- Animated hero: the featured Lexus LX 570 photo assembles from puzzle-piece shards on load (GSAP) and disassembles again as you scroll past, with a subtle mouse-parallax tilt, staged on a soft grey "product plinth" panel.
- Full inventory grid of all 42 cars from the current stock list, each with a real matching photo, brand/year badges, an "estimated price" tag (from the given "demand" prices), spec tags, and a detail modal with a WhatsApp enquiry link pre-filled with the car's name and price.
- Brand filter bar, "by the numbers" stats with count-up animation, animated scroll reveals, a showroom photo gallery, "why us" trust section, and a contact section with all phone numbers, address and an embedded map.
- One deliberate dark section (the showroom gallery) for visual rhythm, the way Apple alternates light and dark sections rather than staying all-white or all-black.
- Logo cropped from the showroom signage photo (`assets/logo/mr-logo.png`).

## Car photos

All 42 listings now have a real photo (`assets/cars/01.jpg` … `42.jpg`), fetched via Apify and matched to each car's brand/model/year. See `assets/cars/manifest.json` for the source and match quality of every photo — most are exact year/trim matches; a handful are the closest available substitute where an exact photo couldn't be found (e.g. an adjacent model year of the same generation, or a different body style of the same nameplate). Worth a quick visual check against the real cars before final launch, especially the ones marked `APPROX` in the manifest.

If a photo ever goes missing, the card gracefully falls back to a clean branded placeholder (brand name, model, accent color) rather than a broken image — the `<img>` tags already point at the `assets/cars/NN.jpg` naming convention, so dropping in a replacement file needs no code changes.

## Adding cars / photos yourself

`admin.html` is a separate page for adding, editing and removing listings without touching code — brand, model, year, price, tags, description and a photo upload. It's published as its own private Claude Artifact (backed by that platform's shared database and asset store), separate from the public site, so it needs to be shared explicitly with **"Can edit" access** (via the Share menu, not just the link) for whoever should be able to add cars.

This admin database is the editable source of new/updated listings. Because the public site is a static file (for reliability and so it works once hosted on your own domain), new entries added in the admin page need a resync into `index.html`'s `CARS` array before they show up live — ask Claude to pull the latest from the admin database and rebuild the site when you've added something.

## Next steps before going live

- Spot-check the `APPROX`-flagged photos in `assets/cars/manifest.json` against the actual cars in stock, and swap in the showroom's own photos where it matters most (especially the Lexus hero car, which already uses a real photo of your own unit).
- Confirm/replace the placeholder Google Maps embed query with the exact pin once available.
- Once a domain is purchased, this can be deployed as-is (static HTML) or migrated into a framework via the `ui-ux-pro-max` skill's `--stack` option if a CMS/backend is needed later.
