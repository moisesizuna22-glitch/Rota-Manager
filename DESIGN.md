---
name: Rota Manager
description: A field terminal for delivery routes — industrial dispatch chrome with an RPG leveling layer that rewards fixing addresses.
colors:
  void-navy: "#0a0c16"
  panel-navy: "#12152a"
  panel-navy-raised: "#161a33"
  hairline: "#262b4a"
  warning-amber: "#f5a623"
  electric-indigo: "#6c63ff"
  signal-green: "#2bb583"
  paper-text: "#e7e9f5"
  muted-slate: "#8d93ad"
  alert-rose: "#e35c84"
  sidebar-void: "#060814"
  sidebar-active-indigo: "#4338ca"
  bg-light: "#f6f7fb"
  surface-light: "#ffffff"
  surface2-light: "#fafbfd"
  hairline-light: "#e3e6ee"
  amber-light: "#d97706"
  indigo-light: "#4338ca"
  green-light: "#0d9265"
  text-light: "#161a2b"
  muted-light: "#5b6478"
  rose-light: "#c4264f"
typography:
  display:
    fontFamily: "Oswald, Inter, system-ui, sans-serif"
    fontSize: "1.75rem"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "0.06em"
  body:
    fontFamily: "Inter, 'Segoe UI', system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  label:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "11px"
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: "0.06em"
  mono:
    fontFamily: "'JetBrains Mono', Consolas, monospace"
    fontSize: "12px"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "normal"
rounded:
  xs: "3px"
  sm: "6px"
  md: "8px"
  lg: "12px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.warning-amber}"
    textColor: "#000000"
    typography: "{typography.label}"
    rounded: "{rounded.xs}"
    padding: "8px 18px"
  button-secondary:
    backgroundColor: "{colors.panel-navy}"
    textColor: "{colors.paper-text}"
    typography: "{typography.label}"
    rounded: "{rounded.xs}"
    padding: "8px 18px"
  button-blue:
    backgroundColor: "{colors.electric-indigo}"
    textColor: "#ffffff"
    typography: "{typography.label}"
    rounded: "{rounded.xs}"
    padding: "8px 18px"
  input-field:
    backgroundColor: "{colors.panel-navy-raised}"
    textColor: "{colors.paper-text}"
    typography: "{typography.body}"
    rounded: "{rounded.xs}"
    height: "44px"
    padding: "0 12px"
  nav-item-active:
    backgroundColor: "{colors.sidebar-active-indigo}"
    textColor: "#ffffff"
    typography: "{typography.body}"
    rounded: "{rounded.lg}"
    padding: "9px 10px"
---

# Design System: Rota Manager

## 1. Overview

**Creative North Star: "The Field Terminal"**

Rota Manager is built for the cab of a delivery vehicle, not a desk. The system reads as rugged dispatch equipment first: a near-black navy base, hairline dividers, uppercase tracked labels, a repeating diagonal hazard stripe on the login card, and a mono readout for coordinates. It has to survive being glanced at one-handed, in motion, in direct sun. Layered on top of that industrial base is the product's actual differentiator: a pixel-art RPG leveling system (avatar, XP bar, badges, item drops) that turns the unglamorous work of correcting an address into visible, earned progress. The two layers don't compete — the terminal is the chassis, the game is the reward system riding inside it.

This system explicitly rejects a childish or cartoonish game skin. The pixel art is deliberate craft (16×16 avatar grids, `image-rendering: pixelated`, tiered badge iconography from anão to grão-mestre), not a cutesy wrapper — it should read as earned insignia, closer to a field ribbon than a mascot. It also rejects generic corporate SaaS chrome; the amber hazard-stripe motif and mono coordinate readouts are the brand's own vocabulary and should never flatten into a gray enterprise dashboard.

**Key Characteristics:**
- Dark navy field-terminal base, light theme available as a secondary mode, same tokens re-mapped
- Amber (warning-tape) as the primary action and achievement color; electric indigo as the cooler secondary/active-state color
- Oswald uppercase-tracked display type for anything ceremonial (headers, login logo, prices, level titles); Inter for everyday UI; JetBrains Mono for coordinates and data readouts
- Flat tonal surfaces at rest; shadow appears only on modals, drawers, and interactive state changes
- Pixel-art gamification components sit inside otherwise sharp, low-radius industrial chrome
- Every animation respects `prefers-reduced-motion`; loading indicators (spinner, progress bar) slow down rather than disappear, so a "still working" signal survives even with motion reduced
- Every interactive control resolves to a 44×44px touch target on mobile, even when the visual icon stays small — this isn't a nice-to-have, it's the outdoor/one-handed-use baseline from PRODUCT.md

## 2. Colors

The palette is warning-tape amber against a near-black navy field, with electric indigo as the one cool counterpoint — high-contrast by design, since it has to hold up in direct sunlight on a phone.

### Primary
- **Warning Amber** (`#f5a623`): the hazard-stripe accent. Primary buttons, XP fill, level badges, active login tab, the diagonal stripe across the top of the login card. It is the color of "progress" and "go" throughout the app.

### Secondary
- **Electric Indigo** (`#6c63ff` dark theme, `#4338ca` in the sidebar and light theme): the cooler counterpoint. Active sidebar nav state, secondary CTAs (`.btn-blue`), the "popular plan" outline, focus rings on inputs. Reserved for navigation/selection state, not achievement.

### Tertiary
- **Signal Green** (`#2bb583`): confirmation actions and positive states only (`.btn-green`), kept rare so it reads as "done/safe" rather than a third brand color competing with amber.

### Neutral
- **Void Navy** (`#0a0c16`): page background, the darkest layer.
- **Panel Navy** (`#12152a`) / **Panel Navy Raised** (`#161a33`): the two-step surface system — cards and panels sit on Panel Navy, nested/recessed elements (stat boxes, input fields, XP track background) sit on Panel Navy Raised.
- **Hairline** (`#262b4a`): all borders and dividers.
- **Paper Text** (`#e7e9f5`): primary text.
- **Muted Slate** (`#8d93ad`): secondary text, labels, placeholder-equivalent copy — kept light enough to read as intentional hierarchy, not a contrast failure.
- **Alert Rose** (`#e35c84`): errors only.
- **Sidebar Void** (`#060814`): the sidebar is a full shade darker than the page body, establishing it as permanent chrome rather than another content panel.

Light theme remaps every neutral (`bg-light` `#f6f7fb`, `surface-light` `#ffffff`, `text-light` `#161a2b`, etc.) and deepens both accents for AA contrast on white (`amber-light` `#d97706`, `indigo-light` `#4338ca`). Same roles, same rules, just inverted — never introduce a new hue for the light theme. `muted-light` was darkened from its original `#677088` to `#5b6478` after an audit found it landed at ≈4.48:1 against white — just under the 4.5:1 AA floor for body-sized text and placeholders; the new value clears it at ≈5.9:1.

### Named Rules
**The Hazard Stripe Rule.** Amber is the only color allowed to read as an alert-adjacent industrial signal (diagonal stripes, XP glow, badge accents). If a new decorative motif wants "attention-grabbing," it's amber-based or it doesn't ship.

**The One Cool Voice Rule.** Electric indigo is the only cool accent in the system. It marks selection and navigation state exclusively — never repurpose it for a second "brand" color role alongside amber.

## 3. Typography

**Display Font:** Oswald (with Inter, system-ui fallback)
**Body Font:** Inter (with Segoe UI, system-ui fallback)
**Label/Mono Font:** JetBrains Mono

**Character:** Oswald's condensed, uppercase-tracked weight carries the industrial/dispatch-board voice — it's used ceremonially, never for body copy. Inter stays invisible and efficient for everything a user actually reads at length. JetBrains Mono signals "this is raw data" (coordinates, hashes) the moment it appears, which is exactly its job.

### Hierarchy
- **Display** (700, 1.75rem representative / ranges 18–32px across contexts, line-height 1.1, letter-spacing 0.06–0.12em, uppercase): login logo, section headers (`#admin-header .title`, `#mapa-header .title`), pricing numbers, level titles. Always uppercase, always tracked wide.
- **Label** (700, 11px, letter-spacing 0.06em, uppercase): field labels, nav section labels, button text, stat captions (`.gami-label`, `.nav-section-label`). This is the system's most-repeated type style — treat it as the default UI voice, not body text.
- **Body** (400, 14px, line-height 1.5): general copy, modal text, form values. Caps at conversational line lengths inside modals (~60–70ch).
- **Mono** (500, 12px): coordinate readouts (`#coord-display`), status codes, anything that reads as machine output rather than authored copy.

### Named Rules
**The All-Caps Ceremony Rule.** Display and Label type are never sentence case. If a heading or button needs lowercase for readability, it isn't a Display/Label use — it belongs in Body.

## 4. Elevation

Flat by default, shadow on state change. Depth at rest comes from the two-step tonal surface system (Panel Navy → Panel Navy Raised), not shadows — cards, stat boxes, and panels sit at the same elevation as their container and differentiate by fill color alone. Shadows are reserved for things that temporarily float above the page: modals, slide-in drawers/sidebars, the login card, dropdown suggestion lists, and hover/active feedback on buttons.

### Shadow Vocabulary
- **Ambient small** (`box-shadow: 0 1px 2px rgba(0,0,0,.4)` dark / `0 1px 2px rgba(17,20,42,.06)` light): sticky header, low-emphasis resting elevation.
- **Ambient medium** (`0 6px 20px rgba(0,0,0,.45)` dark): dropdowns, popovers, moderate floating elements.
- **Ambient large** (`0 12px 36px rgba(0,0,0,.55)` dark): sidebar, drawers, the login card, full modals.
- **Drawer sweep** (`-4px 0 32px rgba(0,0,0,.5)`): the recurring treatment for right-side slide-in panels (history, admin, map, subscription).
- **Inset highlight** (`inset 0 1px 0 rgba(255,255,255,.12)` layered under the ambient shadow): the top-edge sheen on every raised button — this is what makes buttons read as physical/pressable rather than flat color chips.

### Named Rules
**The Press-and-Release Rule.** Buttons carry an inset top highlight plus a drop shadow at rest, and both disappear (via `transform: translateY(1px)`) on active/press. Depth communicates "pressable," not "important."

**The Reduced-Motion Floor Rule.** Every keyframe animation and transition in the system goes near-instant under `prefers-reduced-motion: reduce`, with one narrow exception: indicators whose entire job is signaling "still working" (the loading spinner, the pipeline's indeterminate progress bar) slow down instead of vanishing, so the user never loses the "is this done yet" signal.

## 5. Components

### Buttons
- **Shape:** sharp, 3px radius — deliberately tighter than every other radius in the system, reinforcing the industrial-hardware feel.
- **Primary:** amber fill, black text, uppercase 12px label type, inset highlight + drop shadow (`.btn-primary`).
- **Secondary:** Panel Navy fill with a hairline border (`.btn-secondary`), same shape and label type as primary.
- **Blue / Green variants:** identical shape and type, swap fill to Electric Indigo (`.btn-blue`) or Signal Green (`.btn-green`) for secondary-action and confirm-action semantics respectively.
- **Hover / Active:** `filter: brightness(1.12)` on hover, `translateY(1px)` with shadow removed on active. Disabled drops to 0.4 opacity and strips the filter entirely.
- **Standard transition list:** the `--btn-transition` custom property (`background, color, border-color, box-shadow, opacity, filter, transform`, each at `.15s`) — every button/icon-control references it via `transition: var(--btn-transition)` rather than repeating the list. Never `transition: all`; it silently starts animating whatever layout property gets added later.
- **Touch target floor:** icon-only controls (map buttons, panel close buttons, delete buttons) hit 44×44px on mobile even when the visual box is smaller — either by growing the box itself (close buttons, delete buttons) or, when the control sits inline in a dense table row and growing the box would break alignment, by an invisible `padding` + negative `margin` pair that expands only the hit area (`.btn-ungroup`, `.toggle-pass`).

### Cards / Containers
- **Corner Style:** 10–12px radius for card-level containers (pricing cards, login card) — one step looser than the interior `radius-md` (8px) used for nested elements.
- **Background:** Panel Navy Raised for cards sitting on the page body; the "popular" plan variant adds a 1px Electric Indigo ring instead of a shadow to signal emphasis without breaking the flat-elevation rule.
- **Shadow Strategy:** none at rest (see Elevation); the login card is the one exception, since it floats over a full-bleed backdrop rather than sitting in page flow.
- **Border:** 1px Hairline by default.
- **Internal Padding:** 16–20px for panel-level cards, tighter 8px for nested stat boxes.

### Inputs / Fields
- **Style:** Panel Navy Raised fill, 1px Hairline border, sharp radius (matches buttons, not the looser card radius) — inputs read as part of the same hardware family as buttons.
- **Focus:** border color shifts to Electric Indigo; no glow or ring, keeping the sunlight-readable high-contrast philosophy intact.
- **Error:** Alert Rose background wash at 12% opacity with a matching border, never just red text alone.

### Navigation
- **Style:** icon + label rows on a near-black sidebar void, 0.65 white-alpha at rest, full white on hover, solid Sidebar Active Indigo fill with a soft indigo glow shadow on the active route. Collapses to icon-only at 60px with label opacity/width transitions, not a hard cut.

### Gamification Panel (signature component)
The system's actual differentiator. A 16×16 pixelated avatar grid with a circular level badge overlapping its bottom-right corner; an amber-to-green gradient XP fill inside a Panel Navy Raised track; three stat boxes (paradas/pacotes/endereços) in the nested-surface style; locked badge/item slots rendered at 35% opacity and grayscale until earned. The toast that fires on XP gain reuses the card vocabulary (Panel Navy, amber border, drop shadow) rather than inventing a game-specific alert style — even the celebratory moment stays inside the terminal's chrome.

## 6. Do's and Don'ts

### Do:
- **Do** keep amber as the only "achievement/attention" signal — XP, primary actions, and the login hazard stripe all share one color language.
- **Do** use the sharp 3px radius for anything interactive (buttons, inputs) and reserve the looser 10–12px radius for passive containers (cards, the login shell).
- **Do** default every new surface to flat + tonal layering; add a shadow only when the element temporarily floats (modal, drawer, dropdown, hover state).
- **Do** treat the pixel-art gamification assets as earned insignia — crisp, `image-rendering: pixelated`, tiered by real accomplishment (level, XP milestones).
- **Do** verify contrast for anything read outdoors: this app's baseline assumption is a driver squinting at a phone in sunlight, not an office monitor.

### Don't:
- **Don't** let gamification tip childish or cartoonish — no mascot faces, no bouncy/elastic easing, no candy-bright secondary palette. The RPG layer is earned insignia, not a kids'-app skin.
- **Don't** flatten this into a generic corporate SaaS dashboard — no gray-and-blue enterprise chrome, no default Material card grid. The hazard-stripe amber and mono readouts are the brand's real signature.
- **Don't** introduce a second cool accent color alongside Electric Indigo, and don't reuse Electric Indigo for anything other than navigation/selection state.
- **Don't** add resting-state shadows to cards or panels — depth comes from the two-step navy tonal system, not drop shadows, except on the explicitly floating surfaces named in Elevation.
- **Don't** use border-left/border-right colored stripes as a callout pattern — the system's one "stripe" motif is the diagonal hazard stripe on the login card specifically, not a general-purpose accent border.
