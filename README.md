# NumberInbox site

Static privacy policy and web presence. No build step, no external font service.

## Pages and routes

- `/privacy` → `index.html` (privacy policy; production rewrite in `_redirects`).
- `/delete-account` → `delete-account.html` through Cloudflare Pages' native clean-URL handling (deletion guidance plus a form that prepares a `mailto:` draft; sending stays user-controlled).
- Shared styling: `styles.css`. Brand artwork: `assets/numberinbox-*.svg`.

## Canonical sources

- Brand specification: platform `docs/16-branding.md` (marked color table is authoritative).
- Mobile palette baseline: `mobile-app/core/lib/presentation/resources/numberinbox_palette.dart`.
- Editable master artwork: `mobile-app/assets/brand/source/`
  (`logo-horizontal.svg`, `mark-full-color.svg`, `mark-monochrome-white.svg`).

## Palette and artwork updates

1. Change the canonical guide and mobile palette together; site CSS follows them.
2. Copy approved SVG masters byte for byte into `assets/` without rewriting markup.
3. Recompute hashes and update `assets/brand-manifest.json` (never leave placeholders).
4. Run `python3 scripts/check_brand.py --require-sources` from a checkout with
   `platform` and `mobile-app` siblings present.

## Local preview and verification

```sh
python3 scripts/preview.py --port 8000
python3 scripts/check_brand.py
python3 scripts/check_brand.py --require-sources
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s scripts -p 'test_*.py'
python3 scripts/check_brand.py \
  --platform-root /absolute/path/platform \
  --mobile-root /absolute/path/mobile-app \
  --require-sources
```

Preview binds only `127.0.0.1`, reads exact 200 proxies from `_redirects`,
and mirrors Pages' `.html` canonicalization and extensionless HTML serving
for GET and HEAD requests. This exposes clean-URL self-redirects locally.

Keep only the `/privacy / 200` proxy. Do not add
`/delete-account /delete-account.html 200`: Pages redirects `.html` back to
the extensionless URL, causing a loop. `/delete-account` works natively.
See [Cloudflare Pages route matching](https://developers.cloudflare.com/pages/configuration/serving-pages/#route-matching).

## Fonts and provenance

- Family: Inter 4.1, self-hosted variable `assets/fonts/InterVariable.woff2`.
- Upstream: https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip
- License: `assets/fonts/Inter-LICENSE.txt` (full upstream text).
- Digests are recorded in `assets/brand-manifest.json`.
- In an isolated checkout the checker runs local checks and skips sibling
  comparisons; with `--require-sources` (or explicit roots) missing siblings
  are failures. An explicitly supplied invalid root is always a failure.
