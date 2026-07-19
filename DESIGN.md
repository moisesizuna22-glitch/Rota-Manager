---
name: Rota Manager
description: A cartridge-chrome field terminal for delivery routes — the courier flow reads as a handheld game's quest log and HUD, built on the same industrial-grade structure as before, now in an olive/lime duotone instead of navy/amber.
colors:
  case-olive: "#12160d"
  panel-olive: "#1b2418"
  panel-olive-raised: "#232f1c"
  hairline: "#39432c"
  amber-lime: "#c7d34a"
  signal-teal: "#4f9a90"
  confirm-green: "#5a9e4f"
  paper-text: "#e8e6d9"
  muted-olive: "#8f9878"
  alert-rust: "#c9604a"
  sidebar-void: "#0f120b"
  sidebar-active-teal: "#2f6b62"
  bg-light: "#eeece0"
  surface-light: "#f8f7ef"
  surface2-light: "#f1efe0"
  hairline-light: "#dcd8c4"
  amber-lime-light: "#6b5d0e"
  teal-light: "#2f6b62"
  green-light: "#3f7a2e"
  text-light: "#1c1f14"
  muted-light: "#63684f"
  rust-light: "#a5432e"
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
    backgroundColor: "{colors.amber-lime}"
    textColor: "#14170f"
    typography: "{typography.label}"
    rounded: "{rounded.xs}"
    padding: "8px 18px"
  button-secondary:
    backgroundColor: "{colors.panel-olive}"
    textColor: "{colors.paper-text}"
    typography: "{typography.label}"
    rounded: "{rounded.xs}"
    padding: "8px 18px"
  button-blue:
    backgroundColor: "{colors.signal-teal}"
    textColor: "#ffffff"
    typography: "{typography.label}"
    rounded: "{rounded.xs}"
    padding: "8px 18px"
  input-field:
    backgroundColor: "{colors.panel-olive-raised}"
    textColor: "{colors.paper-text}"
    typography: "{typography.body}"
    rounded: "{rounded.xs}"
    height: "44px"
    padding: "0 12px"
  nav-item-active:
    backgroundColor: "{colors.sidebar-active-teal}"
    textColor: "#ffffff"
    typography: "{typography.body}"
    rounded: "{rounded.lg}"
    padding: "9px 10px"
---

# Design System: Rota Manager

## 1. Overview

**Creative North Star: "Cartridge Chrome"**

Rota Manager is built for the cab of a delivery vehicle, not a desk. The system now reads as a rugged handheld game cartridge rather than a dispatch console: a deep olive-black base, hairline dividers, uppercase tracked labels, and a mono readout for coordinates — still built to survive being glanced at one-handed, in motion, in direct sun, but retinted so the RPG layer stops feeling like a widget bolted onto industrial chrome and starts feeling like the chassis itself. The product's actual differentiator — a pixel-art RPG leveling system (avatar, XP bar, badges, item drops, and now a full-screen level-up moment) — is no longer contained to a side panel; the courier flow is structured around it (quest-log stop list, persistent XP/level HUD).

This system explicitly rejects a childish or cartoonish game skin. The pixel art is deliberate craft (16×16 avatar grids, `image-rendering: pixelated`, tiered badge iconography from anão to grão-mestre), not a cutesy wrapper — it should read as earned insignia, closer to a field ribbon than a mascot. The palette is deliberately muted/adult (olive, lime, teal, bone) rather than the candy-bright palette a literal handheld-console reference would suggest — that was a conscious choice, not a database default. The admin flow stays entirely outside this metaphor by construction: it has no level/XP/avatar fields anywhere in its markup, only account, plan, and access data — "two personas, two speeds" from PRODUCT.md, enforced structurally, not just by convention.

**Key Characteristics:**
- Deep olive-black cartridge-chrome base, light theme available as a secondary mode, same tokens re-mapped
- Amber-lime as the primary action and achievement color; a muted teal as the cooler secondary/active-state color
- Oswald uppercase-tracked display type for anything ceremonial (headers, login logo, prices, level titles); Inter for everyday UI; JetBrains Mono for coordinates and data readouts — typography is unchanged from the previous system, only the palette shifted
- Flat tonal surfaces at rest; shadow appears only on modals, drawers, and interactive state changes
- The gamification panel (`.gami-panel`) carries a subtle accent seam/glow so it reads as a character-sheet module, not a quiet settings row
- Level-up is the **one** moment gamification takes over the full screen (`#levelup-overlay`, reusing the same `_abrirOverlayAnimado` pattern as every other panel); plain XP gains and unlocked cosmetics stay a small toast — "earn, don't decorate" means the escalation is reserved for the moment that's actually rare
- Every animation respects `prefers-reduced-motion`; loading indicators (spinner, progress bar) slow down rather than disappear, so a "still working" signal survives even with motion reduced
- Every interactive control resolves to a 44×44px touch target on mobile, even when the visual icon stays small — this isn't a nice-to-have, it's the outdoor/one-handed-use baseline from PRODUCT.md

## 2. Colors

The palette is amber-lime against a deep olive-black field, with a muted teal as the one cool counterpoint — high-contrast by design, since it has to hold up in direct sunlight on a phone. This replaces the earlier warning-tape-amber/navy/indigo palette; every role and rule below is the same shape as before, just retinted.

### Primary
- **Amber Lime** (`#c7d34a`): the achievement accent. Primary buttons, XP fill, level badges, the level-up overlay's border/glow. It is the color of "progress" and "go" throughout the app.

### Secondary
- **Signal Teal** (`#4f9a90` dark theme, `#2f6b62` in the sidebar and light theme): the cooler counterpoint. Active sidebar nav state, secondary CTAs (`.btn-blue`), focus rings on inputs. Reserved for navigation/selection state, not achievement.

### Tertiary
- **Confirm Green** (`#5a9e4f`): confirmation actions and positive states only (`.btn-green`, HERE-validated badges), kept rare so it reads as "done/safe" rather than a third brand color competing with the amber-lime accent.

### Neutral
- **Case Olive** (`#12160d`): page background, the darkest layer.
- **Panel Olive** (`#1b2418`) / **Panel Olive Raised** (`#232f1c`): the two-step surface system — cards and panels sit on Panel Olive, nested/recessed elements (stat boxes, input fields, XP track background) sit on Panel Olive Raised.
- **Hairline** (`#39432c`): all borders and dividers.
- **Paper Text** (`#e8e6d9`): primary text.
- **Muted Olive** (`#8f9878`): secondary text, labels, placeholder-equivalent copy — kept light enough to read as intentional hierarchy, not a contrast failure.
- **Alert Rust** (`#c9604a`): errors only.
- **Sidebar Void** (`#0f120b`): the sidebar is a full shade darker than the page body, establishing it as permanent chrome rather than another content panel — and now stays this same dark olive-black in both themes, since it's chrome, not content.

Light theme remaps every neutral (`bg-light` `#eeece0`, `surface-light` `#f8f7ef`, `text-light` `#1c1f14`, etc.) and deepens both accents for AA contrast on the paper background (`amber-lime-light` `#6b5d0e`, `teal-light` `#2f6b62`). Same roles, same rules, just inverted — never introduce a new hue for the light theme.

### Named Rules
**The Hazard Stripe Rule.** Amber-lime is the only color allowed to read as an achievement-adjacent signal (XP glow, badge accents, the level-up overlay border). If a new decorative motif wants "attention-grabbing," it's amber-lime-based or it doesn't ship.

**The One Cool Voice Rule.** Signal teal is the only cool accent in the system. It marks selection and navigation state exclusively — never repurpose it for a second "brand" color role alongside amber-lime.

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

Flat by default, shadow on state change. Depth at rest comes from the two-step tonal surface system (Panel Olive → Panel Olive Raised), not shadows — cards, stat boxes, and panels sit at the same elevation as their container and differentiate by fill color alone. Shadows are reserved for things that temporarily float above the page: modals, slide-in drawers/sidebars, the login card, the level-up overlay, dropdown suggestion lists, and hover/active feedback on buttons.

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
- **Primary:** amber-lime fill, near-black ink text, uppercase 12px label type, inset highlight + drop shadow (`.btn-primary`).
- **Secondary:** Panel Olive fill with a hairline border (`.btn-secondary`), same shape and label type as primary.
- **Blue / Green variants:** identical shape and type, swap fill to Signal Teal (`.btn-blue`) or Confirm Green (`.btn-green`) for secondary-action and confirm-action semantics respectively.
- **Hover / Active:** `filter: brightness(1.12)` on hover, `translateY(1px)` with shadow removed on active. Disabled drops to 0.4 opacity and strips the filter entirely.
- **Standard transition list:** the `--btn-transition` custom property (`background, color, border-color, box-shadow, opacity, filter, transform`, each at `.15s`) — every button/icon-control references it via `transition: var(--btn-transition)` rather than repeating the list. Never `transition: all`; it silently starts animating whatever layout property gets added later.
- **Touch target floor:** icon-only controls (map buttons, panel close buttons, delete buttons) hit 44×44px on mobile even when the visual box is smaller — either by growing the box itself (close buttons, delete buttons) or, when the control sits inline in a dense table row and growing the box would break alignment, by an invisible `padding` + negative `margin` pair that expands only the hit area (`.btn-ungroup`, `.toggle-pass`).

### Cards / Containers
- **Corner Style:** 10–12px radius for card-level containers (pricing cards, login card) — one step looser than the interior `radius-md` (8px) used for nested elements.
- **Background:** Panel Olive Raised for cards sitting on the page body; the "popular" plan variant adds a 1px Signal Teal ring instead of a shadow to signal emphasis without breaking the flat-elevation rule.
- **Shadow Strategy:** none at rest (see Elevation); the login card is the one exception, since it floats over a full-bleed backdrop rather than sitting in page flow.
- **Border:** 1px Hairline by default.
- **Internal Padding:** 16–20px for panel-level cards, tighter 8px for nested stat boxes.

### Inputs / Fields
- **Style:** Panel Olive Raised fill, 1px Hairline border, sharp radius (matches buttons, not the looser card radius) — inputs read as part of the same hardware family as buttons.
- **Focus:** border color shifts to Signal Teal; no glow or ring, keeping the sunlight-readable high-contrast philosophy intact.
- **Error:** Alert Rust background wash at 12% opacity with a matching border, never just red text alone.

### Navigation
- **Style:** icon + label rows on a near-black sidebar void, 0.65 white-alpha at rest, full white on hover, solid Sidebar Active Teal fill with a soft teal glow shadow on the active route. Collapses to icon-only at 60px with label opacity/width transitions, not a hard cut.

### Gamification Panel (signature component)
The system's actual differentiator, and now the most visually prominent panel in the courier shell rather than a quiet stat box. A 16×16 pixelated avatar grid with a circular level badge overlapping its bottom-right corner; an amber-lime-to-pale-lime gradient XP fill inside a Panel Olive Raised track; three stat boxes (paradas/pacotes/endereços) in the nested-surface style; locked badge/item slots rendered at 35% opacity and grayscale until earned; the panel itself carries a top accent seam (`inset 0 2px 0` amber-lime) and a faint gradient wash so it reads as a character-sheet module. Plain XP gains and unlocked items still fire a small toast that reuses the card vocabulary (Panel Olive, amber-lime border, drop shadow) — but a level-up escalates to `#levelup-overlay`, a full-screen "save screen" moment (avatar, new level number, XP gained, any new badge), the one place in the app gamification is allowed to take over the whole viewport. It reuses the same `_abrirOverlayAnimado`/zoom-in pattern as every other modal, so it's structurally just another panel, not a bespoke game-UI system.

## 6. Do's and Don'ts

### Do:
- **Do** keep amber-lime as the only "achievement/attention" signal — XP, primary actions, and the level-up overlay all share one color language.
- **Do** use the sharp 3px radius for anything interactive (buttons, inputs) and reserve the looser 10–12px radius for passive containers (cards, the login shell).
- **Do** default every new surface to flat + tonal layering; add a shadow only when the element temporarily floats (modal, drawer, dropdown, hover state, the level-up overlay).
- **Do** treat the pixel-art gamification assets as earned insignia — crisp, `image-rendering: pixelated`, tiered by real accomplishment (level, XP milestones).
- **Do** keep the level-up overlay reserved for actual level-ups only — plain XP gain and item unlocks stay a toast; escalating every gamification event to full-screen would cheapen the one moment that's supposed to feel rare.
- **Do** keep the admin panel free of level/XP/avatar data — it's account and plan management, deliberately outside the game metaphor.
- **Do** verify contrast for anything read outdoors: this app's baseline assumption is a driver squinting at a phone in sunlight, not an office monitor.

### Don't:
- **Don't** let gamification tip childish or cartoonish — no mascot faces, no bouncy/elastic easing, no candy-bright secondary palette. The muted olive/lime duotone is a deliberate choice against the brighter palette a literal handheld-console reference would suggest.
- **Don't** flatten this into a generic corporate SaaS dashboard — no gray-and-blue enterprise chrome, no default Material card grid. The mono coordinate readouts and cartridge-chrome duotone are the brand's real signature.
- **Don't** introduce a second cool accent color alongside Signal Teal, and don't reuse Signal Teal for anything other than navigation/selection state.
- **Don't** add resting-state shadows to cards or panels — depth comes from the two-step olive tonal system, not drop shadows, except on the explicitly floating surfaces named in Elevation.
- **Don't** use border-left/border-right colored stripes as a callout pattern — that motif was retired along with the navy/hazard-stripe system; it isn't part of Cartridge Chrome.
