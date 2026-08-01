Design

1. Visual Theme & Atmosphere

Background & Color Palette
- **Primary Canvas:** Off-white (`#F8F8F7`) for a soft, warm-neutral backdrop (no pure white).
- **Text & Ink:** Near-black ink (`#0d0d0d`) with a subtle teal undertone, cooling the text contrast to prevent eye strain.
- **Borders & Dividers:** Hairline borders (`#e5e5e5`) that act as subtle structure—reading as the absence of color rather than its presence.
- **Chromatic Neutrality:** Designed to keep content, code, and output front and center, minimizing UI chrome.

Typography & Hierarchy
- **Unified Sans (only):** *Inter* everywhere — body, UI, navigation, and headings — at restrained weights:
  - `400` for Body
  - `500` for Navigation & Labels
  - `600` for Emphasis & Headings
- **Mono (technical data only):** system mono for server keys, IPs, session IDs, share links.

Geometry & Layout
- **Shape System:** Uniformly soft with zero harsh corners.
- **Corner Radii:** `8px`–`12px` for cards/containers; `9999px` pills for tags and chips.
- **Spacing:** Section transitions are defined by generous whitespace rather than heavy dividers.

Key Characteristics:

    Off-white canvas (#F8F8F7) with deep teal-black ink (#0d0d0d)
    Inter everywhere (400, 500, 600) — restraint over assertion, no serif
    Mono only for technical data (keys, IPs, IDs)
    Soft 8–12px radii everywhere; 9999px pills for chips
    Hairline borders (#e5e5e5) used sparingly; whitespace as primary divider
    Single-color illustrations in deep teal — no gradients in marks
    Generous line-height (1.55–1.65) and tracking near zero

2. Color Palette & Roles
Primary

    Off-White (#F8F8F7): Primary background (page canvas) — soft warm-neutral instead of pure white.
    Off-White Card (#F8F8F7): Card surface, input background — uniform with the canvas (no pure white surfaces).
    Ink Black (#0d0d0d): Primary text, brand mark, primary CTA.
    Soft Black (#1a1a1a): Secondary heading, alternative ink for non-critical text.

Surface & Background

    Mist (#f2f2f1): Section break background, footer surface (slightly darker than the #F8F8F7 canvas to keep layering visible).
    Pearl (#f5f5f5): Card surface, elevated panel.
    Cloud (#ececec): Disabled background, divider tint.

Brand Accent

    Teal (#10a37f): Brand primary, link, highlight badge — the lone color in an otherwise neutral system.
    Teal Deep (#0a7a5e): Hover and pressed state for the brand color.
    Teal Soft (#e8f5f0): Surface tint for success badges, highlight callouts.

Blue Accent (interactive / navigation)

    Light Mode
        Blue (#2563eb): Primary interactive accent — active nav tab, links, focus rings.
        Blue Deep (#1e40af): Text-on-tint variant for the active state (WCAG-safe on light tint).
        Blue Soft (#dbeafe): Active tab background tint.
        Blue Soft Hover (#bfdbfe): Active tab hover tint.
    Dark Mode
        Blue (#7DD3FC): Active tab text / icon (light-on-dark accent).
        Blue Deep (#7DD3FC): Text-on-tint variant (same as Blue in dark mode).
        Blue Soft (rgba(125,211,252,0.14)): Active tab background tint.
        Blue Soft Hover (rgba(125,211,252,0.20)): Active tab hover tint.

    Usage: sidebar active tab (`.sidebar-link--active`), news/blog eyebrows + pinned pills (`.pill-blue`),
    hero accents on article pages. Defined as CSS custom properties `--blue`, `--blue-deep`,
    `--blue-soft`, `--blue-soft-hover` in both `:root` and `[data-theme="dark"]`.
    Teal remains the brand color; blue is the interactive/navigation accent — kept consistent
    per theme (no hardcoded hex values in templates, always use the tokens).

    Note: `--info` (#2563eb light / #529cca dark) intentionally stays a separate semantic token
    for informational toasts — do not deduplicate it with `--blue` even though they look alike
    in light mode.

Neutrals & Text

    Graphite (#3c3c3c): Body text, default reading color.
    Slate (#6e6e6e): Secondary text, captions, metadata.
    Ash (#9b9b9b): Tertiary text, placeholder, disabled label.
    Stone (#c4c4c4): Decorative dividers, faint icons.

Semantic & Border

    Border Hairline (#e5e5e5): Standard hairline separator.
    Border Soft (#ededed): Card outline on off-white surface.
    Error (#ef4146): Validation, destructive action.
    Warning (#f5a623): Soft amber for advisory states.
    Info (#2563eb): Informational link tone (used sparingly; teal still wins).

3. Typography Rules
Font Family

    UI / Text / Headings: Inter, with fallback: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif
    Mono (technical data only): ui-monospace, 'JetBrains Mono', Menlo, Consolas, monospace

Hierarchy
Role 	Font 	Size 	Weight 	Line Height 	Letter Spacing 	Notes
Display 	Inter 	56px (3.5rem) 	600 	1.08 	-0.02em 	Hero, announcement titles
H1 	Inter 	40px (2.5rem) 	600 	1.15 	-0.01em 	Page heading
H2 	Inter 	28px (1.75rem) 	600 	1.2 	-0.005em 	Section heading
H3 	Inter 	20px (1.25rem) 	600 	1.3 	normal 	Sub-section
Body Large 	Inter 	18px (1.125rem) 	400 	1.6 	normal 	Lede paragraphs
Body 	Inter 	16px (1rem) 	400 	1.65 	normal 	Standard reading text
Body Small 	Inter 	14px (0.875rem) 	400 	1.55 	normal 	Card body, dense UI
Caption 	Inter 	13px (0.8125rem) 	500 	1.4 	0.01em 	Metadata, badges
Label 	Inter 	12px (0.75rem) 	500 	1.3 	0.04em 	Eyebrow, uppercase nav links
Code 	Mono 	14px (0.875rem) 	400 	1.55 	normal 	Server keys, IPs, IDs, share links
Principles

    Restraint as identity: weights cap at 600; 700+ feels off-brand. Hierarchy comes from size and color, not weight.
    One font for everything: Inter is the single typeface — no serif display font. Hierarchy comes from size, weight, and color.
    Negative tracking on display: -0.02em on display sizes; tracking returns to zero by 16px.

4. Component Stylings
Buttons

Primary

    Background: #0d0d0d
    Text: #ffffff
    Padding: 10px 18px
    Radius: 9999px (full pill) on chips, 12px on rectangular CTAs
    Hover: #1a1a1a background
    Use: Primary CTA, "Sign in"

Secondary

    Background: #f1f1f1
    Text: #171717
    Border: none
    Padding: 10px 18px
    Radius: 12px
    Hover: background #f1f1f1

Brand Accent

    Background: #10a37f
    Text: #ffffff
    Padding: 10px 18px
    Radius: 12px
    Hover: #0a7a5e
    Use: Highlighted upgrade CTA, success path

Cards

    Background: #F8F8F7
    Border: 1px solid #ededed
    Radius: 16px
    Padding: 24px–32px
    Shadow: none by default; on hover 0 4px 16px rgba(13,13,13,0.06)

Inputs

    Background: #F8F8F7
    Border: 1px solid #e5e5e5
    Radius: 12px
    Padding: 12px 14px
    Focus: border #262626, ring 0 0 0 3px rgba(38,38,38,0.08)

Pills & Tags

    Background: #f5f5f5
    Text: #3c3c3c
    Padding: 4px 10px
    Radius: 9999px
    Font: 12px / 500

5. Spacing & Layout

    Base unit: 4px. Scale: 4, 8, 12, 16, 24, 32, 48, 64, 96, 128.
    Container: max-width 1200px, 24px gutter on mobile, 48px on desktop.
    Section rhythm: 96–128px vertical between major sections; 64px on mobile.
    Grid: 12-column desktop, 4-column mobile, 24px gap.

6. Motion

    Duration: 150–220ms for hover; 280–360ms for layout transitions.
    Easing: cubic-bezier(0.16, 1, 0.3, 1) (smooth out) for entrances.
    Restraint: no parallax, no scroll-jacking. Subtle fade and translate only.
