# fonts/

Place brand-specific font files here if you need to load them locally (e.g. in offline environments).

The HTML templates currently load fonts from Google Fonts CDN:
- **Sora** — headings
- **Manrope** — body copy
- **Cormorant Garamond** — accent/editorial
- **Tiro Devanagari Hindi** — Hindi / Punjabi text in festival templates

For offline use, download the TTF/WOFF2 files from fonts.google.com and update the `<link>` tags in the HTML templates to use local `@font-face` declarations pointing here.
