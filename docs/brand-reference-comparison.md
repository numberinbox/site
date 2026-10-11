# Brand board vs approved SVG masters — visual comparison

Date: October 11, 2026 (Asia/Bangkok). Scope: audit only; no artwork was redrawn.

Reference: the supplied NumberInbox brand board (raster PNG, designer export).
Masters: `assets/numberinbox-logo.svg`, `assets/numberinbox-mark.svg`
(byte-identical to the mobile masters; see `assets/brand-manifest.json`).

Method: the board was inspected at full size and the masters were inspected
as vector source plus rendered at a large comparison size (~235px mark,
~265px wordmark) and at the website header size (190–265px desktop wordmark,
172px mobile). Vector construction below is quoted from the SVG source.

## Observations

- N silhouette: the board builds the mark from two upright rounded stems
  crossed by a wide diagonal ribbon. The masters use the same construction:
  two stadium-ended rects (132 wide, rx 66) plus a −45° rotated rounded bar.
- Corner rounding: board stems read as fully rounded pills; the masters use
  matching stadium ends on stems and ribbon. Consistent.
- @ glyph: board shows a bold white ring-and-tail centered on the crossing.
  The masters draw a centered white-stroked circle (r 29) with a tail path in
  the same position. Consistent in shape and placement.
- Wordmark: board sets “Number” in near-black navy with “Inbox” running
  blue→cyan→green. The masters fill the “Number” outlines with `#0F172A`
  and the “Inbox” outlines with a blue→cyan→green gradient. Roles match; the
  letterforms are outline-traced paths, so an exact typeface match to the
  board is not asserted from source.
- Gradient direction and depth: board flows green (left) into blue (right)
  along the mark diagonal with soft depth shading. The masters run
  green→teal→blue along the same diagonal with highlight/shadow stops.
  Same direction and comparable depth treatment.
- Logo-to-text scale and clear space: the board pairs the mark with a
  wordmark roughly twice the mark height and generous clear space. The
  website reserves a clamp(190px, 25vw, 265px) header lockup (172px on
  mobile) with wrapping instead of clipping, preserving clear space.

## Conclusion

No fidelity defect was confirmed. The masters reproduce the board's
construction, palette roles, and lockup proportions; exact-copy status
between raster export and vector masters is not claimed. Artwork is
preserved unchanged under the default scope. If a pixel-level audit is
wanted later, scope it as a separate artwork task.
