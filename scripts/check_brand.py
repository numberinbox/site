#!/usr/bin/env python3
"""NumberInbox brand checker (stdlib only).

Local checks always run; sibling platform/mobile sources are compared when
available. See docs/plans/2026-10-10-brand-standardization.md section 6.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PRIMITIVES = {
    "--color-navy": "#0F172A",
    "--color-emerald": "#10B981",
    "--color-cyan": "#06B6D4",
    "--color-gray": "#E5E7EB",
    "--color-ice": "#F5F7EB",
    "--color-white": "#FFFFFF",
    "--color-action-green": "#047857",
    "--color-action-green-hover": "#065F46",
    "--color-action-blue": "#0369A1",
    "--color-action-blue-hover": "#075985",
    "--color-slate": "#475569",
    "--color-mint": "#DDF7EC",
    "--color-danger": "#C0392B",
    "--color-emerald-tint": "#E5FBF1",
    "--color-cyan-tint": "#D7F6FB",
}

REQUIRED_ALIASES = {
    "--text-primary": "--color-navy",
    "--text-secondary": "--color-slate",
    "--surface-page": "--color-ice",
    "--surface-card": "--color-white",
    "--surface-callout": "--color-mint",
    "--border-subtle": "--color-gray",
    "--border-control": "--color-slate",
    "--action-primary": "--color-action-green",
    "--action-primary-hover": "--color-action-green-hover",
    "--link-default": "--color-action-blue",
    "--link-hover": "--color-action-blue-hover",
    "--focus-light": "--color-action-blue",
    "--focus-dark": "--color-white",
}

MOBILE_TO_CSS = {
    "emerald": "--color-emerald",
    "cyan": "--color-cyan",
    "navy": "--color-navy",
    "coolGray": "--color-gray",
    "ice": "--color-ice",
    "actionGreen": "--color-action-green",
    "actionBlue": "--color-action-blue",
    "selection": "--color-mint",
}

# (foreground token, background token, minimum ratio, label)
CONTRAST_CHECKS = [
    ("--color-navy", "--color-ice", 4.5, "navy text on ice"),
    ("--color-slate", "--color-ice", 4.5, "slate text on ice"),
    ("--color-white", "--color-action-green", 4.5, "white text on action green"),
    ("--color-action-blue", "--color-mint", 4.5, "blue links on mint"),
    ("--color-slate", "--color-white", 3.0, "slate field borders on white"),
    ("--color-mint", "--color-navy", 4.5, "mint footer links on navy"),
    ("--color-white", "--color-navy", 4.5, "white footer focus on navy"),
    ("--color-white", "--color-action-green-hover", 4.5, "white text on action-green hover"),
    ("--color-action-blue-hover", "--color-mint", 4.5, "blue hover links on mint"),
    ("--color-action-blue", "--color-white", 4.5, "blue focus on white"),
    ("--color-action-blue", "--color-ice", 4.5, "blue focus on ice"),
    ("--color-action-blue", "--color-mint", 3.0, "blue focus on mint"),
]

EXPECTED_REDIRECTS = {
    "/privacy / 200",
    "/delete-account /delete-account.html 200",
}

ASSET_REFS = [
    "/assets/numberinbox-logo.svg",
    "/assets/numberinbox-mark.svg",
    "/assets/numberinbox-mark-white.svg",
]

EXPECTED_ARTWORK = {
    "assets/numberinbox-logo.svg": "assets/brand/source/logo-horizontal.svg",
    "assets/numberinbox-mark.svg": "assets/brand/source/mark-full-color.svg",
    "assets/numberinbox-mark-white.svg": "assets/brand/source/mark-monochrome-white.svg",
}

FONT_PRELOAD_HREF = "/assets/fonts/InterVariable.woff2"
STYLESHEET_HREF = "/styles.css"
THEME_COLOR = "#0F172A"


def fail(message: str, failures: list[str]) -> None:
    failures.append(message)
    print(f"FAIL {message}")


def ok(message: str) -> None:
    print(f"PASS {message}")


def strip_css_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def parse_custom_properties(block: str) -> dict[str, list[str]]:
    props: dict[str, list[str]] = {}
    for match in re.finditer(r"(--[\w-]+)\s*:\s*([^;]+);", block):
        props.setdefault(match.group(1), []).append(match.group(2).strip())
    return props


def resolve_alias(name: str, props: dict[str, list[str]], seen: tuple[str, ...]) -> str | None:
    if name in seen:
        return None
    values = props.get(name)
    if not values:
        return None
    # Cascade order: the last declaration wins.
    ref = re.search(r"var\(\s*(--[\w-]+)\s*\)", values[-1])
    if not ref:
        return None
    target = ref.group(1)
    if target in REQUIRED_PRIMITIVES:
        return target
    return resolve_alias(target, props, seen + (name,))


def hex_to_rgb(value: str) -> tuple[float, float, float]:
    value = value.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    r = int(value[0:2], 16) / 255.0
    g = int(value[2:4], 16) / 255.0
    b = int(value[4:6], 16) / 255.0
    return (r, g, b)


def linearize(channel: float) -> float:
    if channel <= 0.04045:
        return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4


def luminance(rgb: tuple[float, float, float]) -> float:
    r, g, b = (linearize(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: str, bg: str) -> float:
    l1 = luminance(hex_to_rgb(fg))
    l2 = luminance(hex_to_rgb(bg))
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="NumberInbox brand checker")
    parser.add_argument("--platform-root", default=None)
    parser.add_argument("--mobile-root", default=None)
    parser.add_argument("--require-sources", action="store_true")
    args = parser.parse_args()

    site = SITE_ROOT
    platform_root = Path(args.platform_root) if args.platform_root else site.parent / "platform"
    mobile_root = Path(args.mobile_root) if args.mobile_root else site.parent / "mobile-app"

    failures: list[str] = []

    css_path = site / "styles.css"
    if not css_path.is_file():
        fail("styles.css is missing", failures)
        print(f"{len(failures)} failing check(s)")
        return 1
    css_raw = css_path.read_text(encoding="utf-8")
    css = strip_css_comments(css_raw)
    root_blocks = re.findall(r":root\s*\{(.*?)\}", css, flags=re.S)
    if not root_blocks:
        fail("styles.css has no :root block", failures)
        print(f"{len(failures)} failing check(s)")
        return 1
    # Merge declarations in cascade order (later blocks win) so appended
    # overrides are visible to every check below.
    props: dict[str, list[str]] = {}
    for block in root_blocks:
        for prop_name, prop_values in parse_custom_properties(block).items():
            props.setdefault(prop_name, []).extend(prop_values)

    for name, expected in REQUIRED_PRIMITIVES.items():
        occurrences = len(re.findall(rf"{re.escape(name)}\s*:", css))
        actual_values = props.get(name, [])
        if occurrences != 1:
            fail(f"styles.css token {name} declared {occurrences}x, expected exactly once", failures)
        elif actual_values[-1].strip().upper() != expected.upper():
            fail(f"styles.css token {name} is {actual_values[-1].strip()}, expected {expected}", failures)
        else:
            ok(f"styles.css token {name} = {expected}")

    for alias, expected_target in REQUIRED_ALIASES.items():
        occurrences = len(re.findall(rf"{re.escape(alias)}\s*:", css))
        if occurrences != 1:
            fail(f"styles.css alias {alias} declared {occurrences}x, expected exactly once", failures)
            continue
        resolved = resolve_alias(alias, props, ())
        if resolved != expected_target:
            fail(f"styles.css alias {alias} resolves to {resolved}, expected {expected_target}", failures)
        else:
            ok(f"styles.css alias {alias} -> {expected_target}")

    outside_root = css
    for block in root_blocks:
        outside_root = outside_root.replace(block, "", 1)
    # URLs are not color declarations; strip url(...) before scanning.
    outside_scannable = re.sub(r"url\([^)]*\)", "url()", outside_root)
    color_literal = re.search(
        r"#[0-9A-Fa-f]{3,8}\b|\brgba?\s*\(|\bhsla?\s*\(",
        outside_scannable,
    )
    if color_literal:
        fail(f"styles.css has color literal outside :root: {color_literal.group(0)}", failures)
    else:
        ok("styles.css has no color literals outside :root")

    for page_name in ("index.html", "delete-account.html"):
        page = site / page_name
        if not page.is_file():
            fail(f"{page_name} is missing", failures)
            continue
        html = page.read_text(encoding="utf-8")
        if STYLESHEET_HREF not in html:
            fail(f"{page_name} does not load {STYLESHEET_HREF}", failures)
        else:
            ok(f"{page_name} loads shared stylesheet")
        if FONT_PRELOAD_HREF not in html or "as=\"font\"" not in html and "as='font'" not in html:
            fail(f"{page_name} is missing the local font preload", failures)
        else:
            ok(f"{page_name} preloads local font")
        if THEME_COLOR.lower() not in html.lower():
            fail(f"{page_name} is missing theme color {THEME_COLOR}", failures)
        else:
            ok(f"{page_name} has approved theme color")
        missing_refs = [ref for ref in ASSET_REFS if ref not in html]
        if missing_refs:
            fail(f"{page_name} is missing asset refs: {', '.join(missing_refs)}", failures)
        else:
            ok(f"{page_name} references brand assets")

    font_face = re.search(r"@font-face\s*\{(.*?)\}", css, flags=re.S)
    if not font_face:
        fail("styles.css has no @font-face block", failures)
    else:
        block = font_face.group(1)
        checks = [
            ("font-style: normal" in block, "normal style"),
            ("100 900" in block, "variable weights 100 900"),
            ("font-display: swap" in block, "font-display swap"),
            ("InterVariable.woff2" in block, "local InterVariable.woff2 source"),
        ]
        for passed, label in checks:
            if passed:
                ok(f"@font-face declares {label}")
            else:
                fail(f"@font-face is missing {label}", failures)

    manifest_path = site / "assets" / "brand-manifest.json"
    if not manifest_path.is_file():
        fail("assets/brand-manifest.json is missing", failures)
    else:
        import json

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except ValueError as exc:
            fail(f"assets/brand-manifest.json is not valid JSON: {exc}", failures)
            manifest = None
        if manifest is not None:
            if manifest.get("schemaVersion") != 1:
                fail("assets/brand-manifest.json schemaVersion is not 1", failures)
            else:
                ok("brand manifest schemaVersion = 1")
            declared_artwork = {
                str(entry.get("path", "")): str(entry.get("source", ""))
                for entry in manifest.get("artwork", [])
                if isinstance(entry, dict)
            }
            if declared_artwork != EXPECTED_ARTWORK:
                missing = sorted(set(EXPECTED_ARTWORK) - set(declared_artwork))
                extra = sorted(set(declared_artwork) - set(EXPECTED_ARTWORK))
                mismapped = sorted(
                    path
                    for path in set(declared_artwork) & set(EXPECTED_ARTWORK)
                    if declared_artwork[path] != EXPECTED_ARTWORK[path]
                )
                detail = "; ".join(
                    part
                    for part in [
                        f"missing: {', '.join(missing)}" if missing else "",
                        f"unexpected: {', '.join(extra)}" if extra else "",
                        f"wrong source: {', '.join(mismapped)}" if mismapped else "",
                    ]
                    if part
                )
                fail(f"brand manifest must list exactly the approved artwork ({detail})", failures)
            else:
                ok("brand manifest lists all approved artwork")
            for entry in manifest.get("artwork", []):
                rel = Path(entry.get("path", ""))
                target = (site / rel).resolve()
                try:
                    target.relative_to(site.resolve())
                except ValueError:
                    fail(f"manifest artwork path escapes site root: {rel}", failures)
                    continue
                if not target.is_file():
                    fail(f"manifest artwork file is missing: {rel}", failures)
                    continue
                actual = sha256_file(target)
                if actual != entry.get("sha256"):
                    fail(f"manifest artwork hash mismatch: {rel}", failures)
                else:
                    ok(f"manifest artwork verified: {rel}")
            font = manifest.get("font", {})
            font_path = site / Path(font.get("path", "missing"))
            if not font_path.is_file():
                fail("manifest font file is missing", failures)
            else:
                if font_path.read_bytes()[:4] != b"wOF2":
                    fail("bundled font lacks the WOFF2 signature", failures)
                else:
                    ok("bundled font has WOFF2 signature")
                if sha256_file(font_path) != font.get("sha256"):
                    fail("manifest font hash mismatch", failures)
                else:
                    ok("manifest font hash verified")
            license_path = site / Path(font.get("licensePath", "missing"))
            if not license_path.is_file():
                fail("bundled font license is missing", failures)
            else:
                if sha256_file(license_path) != font.get("licenseSha256"):
                    fail("manifest font license hash mismatch", failures)
                else:
                    ok("manifest font license verified")

    for fg_token, bg_token, minimum, label in CONTRAST_CHECKS:
        fg = REQUIRED_PRIMITIVES[fg_token]
        bg = REQUIRED_PRIMITIVES[bg_token]
        ratio = contrast_ratio(fg, bg)
        if ratio < minimum:
            fail(f"contrast {label} is {ratio:.2f}:1, needs >={minimum}:1", failures)
        else:
            ok(f"contrast {label} {ratio:.2f}:1 >= {minimum}:1")

    redirects_path = site / "_redirects"
    if not redirects_path.is_file():
        fail("_redirects is missing", failures)
    else:
        lines = {
            line.strip()
            for line in redirects_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        if not EXPECTED_REDIRECTS.issubset(lines):
            fail("_redirects is missing a required route mapping", failures)
        else:
            ok("_redirects retains both route mappings")

    # Sibling-source checks.
    platform_guide = platform_root / "docs" / "16-branding.md"
    mobile_palette = (
        mobile_root / "core" / "lib" / "presentation" / "resources" / "numberinbox_palette.dart"
    )
    mobile_sources = [
        mobile_root / "assets" / "brand" / "source" / "logo-horizontal.svg",
        mobile_root / "assets" / "brand" / "source" / "mark-full-color.svg",
        mobile_root / "assets" / "brand" / "source" / "mark-monochrome-white.svg",
    ]
    sources_available = platform_guide.is_file() and mobile_palette.is_file() and all(
        p.is_file() for p in mobile_sources
    )

    def invalid_root(path: Path, label: str) -> bool:
        # An explicitly supplied root must exist and be a directory.
        return not path.is_dir()

    explicit_bad = (
        (args.platform_root and invalid_root(platform_root, "platform"))
        or (args.mobile_root and invalid_root(mobile_root, "mobile"))
    )
    if explicit_bad:
        fail("supplied source root does not exist", failures)
    elif not sources_available:
        message = "sibling platform/mobile sources unavailable; source checks skipped"
        if args.require_sources:
            fail(message + " (--require-sources)", failures)
        else:
            print(f"SKIP {message}")
    else:
        guide_text = platform_guide.read_text(encoding="utf-8")
        marked = re.search(
            r"<!-- numberinbox-brand-colors:start -->(.*?)<!-- numberinbox-brand-colors:end -->",
            guide_text,
            flags=re.S,
        )
        if not marked:
            fail("platform guide is missing the marked brand color table", failures)
        else:
            guide_tokens: dict[str, str] = {}
            for row in marked.group(1).splitlines():
                cells = [c.strip().strip("`") for c in row.strip().strip("|").split("|")]
                if len(cells) == 3 and cells[0].startswith("--color-"):
                    guide_tokens[cells[0]] = cells[1]
            mismatched = [
                name
                for name, value in REQUIRED_PRIMITIVES.items()
                if guide_tokens.get(name, "").upper() != value.upper()
            ]
            if mismatched:
                fail(f"guide tokens differ from CSS: {', '.join(mismatched)}", failures)
            else:
                ok("platform guide tokens match website CSS")

        dart = mobile_palette.read_text(encoding="utf-8")
        dart_values: dict[str, str] = {}
        for match in re.finditer(
            r"static const (\w+)\s*=\s*Color\(0xFF([0-9A-Fa-f]{6})\)", dart
        ):
            dart_values[match.group(1)] = f"#{match.group(2).upper()}"
        mismatched_mobile = []
        for member, css_prop in MOBILE_TO_CSS.items():
            expected = REQUIRED_PRIMITIVES[css_prop]
            if dart_values.get(member, "").upper() != expected.upper():
                mismatched_mobile.append(f"{member} (mobile {dart_values.get(member)} != {expected})")
        if mismatched_mobile:
            fail(f"mobile palette differs from CSS: {', '.join(mismatched_mobile)}", failures)
        else:
            ok("mobile palette matches website tokens")

        site_svg_paths = [
            site / "assets" / "numberinbox-logo.svg",
            site / "assets" / "numberinbox-mark.svg",
            site / "assets" / "numberinbox-mark-white.svg",
        ]
        for local, master in zip(site_svg_paths, mobile_sources):
            if not local.is_file():
                fail(f"site artwork is missing: {local.name}", failures)
            elif local.read_bytes() != master.read_bytes():
                fail(f"site artwork differs from mobile master: {local.name}", failures)
            else:
                ok(f"site artwork matches mobile master: {local.name}")

    if failures:
        print(f"{len(failures)} failing check(s)")
        return 1
    print("All brand checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
