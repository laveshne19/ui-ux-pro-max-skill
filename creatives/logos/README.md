# logos/

Placeholder SVG logos for the three brands. Replace these with the real logo files
before publishing any creative.

| File | Brand | Format |
|------|-------|--------|
| `ne_mark.svg` | Nalanda Enterprises | SVG vector mark |
| `bizwrap.svg` | BizWrap India | SVG wordmark |
| `cgi.svg` | Corporate Gifting India | SVG wordmark |

After placing real logo files here, run:

```bash
python gen_logos.py
```

This converts them to PNG so the HTML templates can reference them via `<img>` tags.
The `brands.json` `logoHtml` field can use either format.

## Adding a real logo

1. Copy your PNG or SVG logo file here (e.g. `nalanda_logo.png`).
2. Update `brands.json` — set `logo` to the relative path (e.g. `logos/nalanda_logo.png`).
3. Update `logoHtml` in `brands.json` to use the new path.
4. Test a render: `node render.js gbp_post '{}' nalanda out/test.png`
