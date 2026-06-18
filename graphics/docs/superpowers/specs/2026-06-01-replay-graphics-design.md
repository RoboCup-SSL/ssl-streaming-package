# Design: Replay graphics — stinger + looping painting-frame overlay (RoboCup 2026 SSL)

**Date:** 2026-06-01
**Status:** Approved (pending spec review)

## Goal

Two new transparent-VP9 graphics for the RoboCup 2026 Small Size League OBS
broadcast, both built around one shared RoboCup 2026 **theme**:

1. **Replay stinger** — an OBS scene transition played *both* into and out of
   replay. The official 5-colour brand bars sweep in from the screen edges, fully
   cover the screen (the scene swap happens here, unseen), then retract and settle
   for a beat into a thin 5-colour **frame border** — the same border the overlay
   wears — before clearing to reveal the new scene.
2. **Replay frame overlay** — a seamlessly **looping** transparent video that sits
   on top of the replay footage for its entire (arbitrary) duration: a sleek
   5-colour painting-frame border with a **"REPLAY"** badge and a gently **pulsing
   dot**.

This is the first feature of a larger broadcast package ("more stingers and frames
will follow"), so it establishes a **central theme module** every future graphic
imports from. The owner knows OBS, not React — all creative knobs stay exposed in
Remotion Studio via Zod schemas.

> **Border redesign (2026-06-01):** the frame is **left→right 5-colour bars**, not
> concentric rings — see the redesign entry in `DESIGN_DECISION_DOCUMENT.md`. The
> sections below are updated to match.

## The frame geometry

The frame's **top and bottom bars** are each split into 5 equal-width colour
segments (20% each), coloured left→right: orange · green · lime · purple · magenta.
The **left edge** is a full-height orange bar, the **right edge** a full-height
magenta bar. The centre is transparent (the footage shows through).

## The unifying idea

Both deliverables are *the same 5-colour frame*; the only difference is its
**thickness over time**.

- **Overlay** = frame at a fixed thin thickness `T`, forever (looping).
- **Stinger** = the identical frame with **animated** thickness: the striped
  top/bottom bars grow inward and **meet in the middle** (→ 5 full vertical stripes
  = full coverage, the OBS swap), then part back, **settle at `T`** for a beat
  (momentarily *becoming* the overlay), then shrink to 0. On the way in the segments
  arrive **left→right** (a per-segment `stagger`) so the sweep reads with the colour
  order.

One `FrameBorder` component renders both, so the stinger's settled frame and the
overlay's border are pixel-identical for free. It also resolves the
hollow-vs-coverage tension: the frame is only hollow when thin; at the covered
moment the top and bottom bars meet into a solid block.

## Central theme module (`src/theme/`)

Single source of truth all stingers and frames import. Tune it once, re-render,
everything updates in lockstep. Studio knobs still exist per composition, but their
**defaults are sourced from these tokens**.

```ts
CANVAS     = { width: 3840, height: 2160 }
FPS        = 60
BRAND      = { orange:'#F26223', green:'#55B748', lime:'#CDDC29',
               purple:'#804FA0', magenta:'#E63D66', paper:'#F5F6FE', ink:'#1a1a1e' }
BRAND_BARS = [orange, green, lime, purple, magenta]   // signature ordered motif (left→right)
FRAME      = { thickness: 120, bands: BRAND_BARS }     // the thin 5-colour frame
TIMING     = { stingerDuration:90, holdFrames:10, settleFrames:12, stagger:4,
               loopDuration:120, pulsePeriod:120 }     // frames @ 60fps
ASSETS     = { mascot:'mascot_with_ball.png', logo:'logo_w.png' }  // served from public/
EASING     = easeInOut                                 // re-exported from Stinger/wipe.ts
```

Brand values sampled from 2026.robocup.org assets (see the project brand memory /
`DESIGN_DECISION_DOCUMENT.md`). `BRAND_BARS` is THE brand hook — a frame built from
those five colours reads instantly as RoboCup 2026. SSL team colours (blue/yellow)
are a *separate* concern and are not part of this theme.

## Choreography math (`src/Replay/frame.ts`, pure)

Reuses `interp` / `easeInOut` / `clamp` / `lerp` from `../Stinger/wipe.ts`.

**`segmentThickness({frame, index, count, stagger, …})` → px** — the top/bottom bar
height for one colour segment during the stinger. In the **grow** phase each segment
rises from 0 to `coverThickness`, arriving **left→right** (segment 0 first, the last
segment exactly at `coverEnd`). From the cover hold onward it returns the uniform
`replayThickness` below, so coverage holds and the frame settles/clears together.

**`replayThickness({frame, duration, holdFrames, settleFrames, coverThickness, frameThickness})` → px**
— the uniform thickness (drives the side edge bars + the settle/reveal of every
segment) across five phases (example: `duration=90, holdFrames=10, settleFrames=12`):

| frames  | phase        | thickness                          |
|---------|--------------|------------------------------------|
| 0 → ~38 | grow         | `0 → coverThickness` (eased)       |
| ~38 → ~48 | cover hold | `coverThickness` — **OBS swaps here** |
| ~48 → ~58 | settle-in  | `coverThickness → frameThickness`  |
| ~58 → ~70 | settle hold| `frameThickness` — *identical to the overlay* (handoff beat) |
| ~70 → 89  | reveal     | `frameThickness → 0`               |

Phase boundaries derive from the tokens (`holdFrames`, `settleFrames`); exact splits
are an implementation detail. **Coverage invariant (load-bearing):**
`coverThickness` defaults to `⌈height/2⌉ = 1080`; at that thickness the top and
bottom bars (full width) meet in the middle and the 3840×2160 canvas is fully
opaque. Every colour segment must be `≥ height/2` for every frame in the cover-hold
window. One symmetric 90-frame clip serves both transition directions in OBS.

**`pulse({frame, period})` → 0…1** — `0.5 + 0.5·sin(2π·frame/period)`. Drives the
REPLAY dot's opacity/scale. Loop-safe because `period` divides `loopDuration`
(theme guard), so the overlay's last rendered frame meets frame 0 with no seam.

## Architecture / files

```
src/theme/
  index.ts          # the design tokens above
src/Replay/
  frame.ts          # PURE: segmentThickness(), replayThickness(), pulse()
  frame.test.ts     # MINIMAL: cover-hold coverage + pulse loop-seam ONLY (see Testing)
  schema.ts         # Zod knobs; defaults sourced from theme tokens
  FrameBorder.tsx   # top/bottom striped bars + side edge bars — shared by stinger AND overlay
  ReplayStinger.tsx # animated-thickness frame + 'REPLAY' cover-hold callout
  ReplayOverlay.tsx # fixed-thickness frame + REPLAY badge + pulsing dot
src/Root.tsx        # MODIFY: register ReplayStinger + ReplayOverlay (defaultProps from theme)
package.json        # MODIFY: render:replay-stinger / render:replay-overlay (+ :preview)
public/             # NEW: Remotion static assets (mascot, logo) for future graphics
DESIGN_DECISION_DOCUMENT.md  # NEW repo-root living decision log
```

The existing `Stinger` and `ChaseStinger` are **untouched** (they keep their own
palettes for now; the theme is built so they can migrate later).

## Components

- **`FrameBorder.tsx`** — props `{ segmentColors, barThickness[], leftThickness,
  rightThickness }`. Renders, per colour segment, a top and a bottom rectangle
  (`width = 100/n %`, height = `barThickness[i]`), plus full-height left/right edge
  bars in the first/last colour. The entire visual of both graphics; the stinger
  animates the thicknesses, the overlay passes uniform values.
- **`ReplayStinger.tsx`** — transparent root → `FrameBorder` whose per-segment
  `barThickness` comes from `segmentThickness(frame, i, …)` (side bars from the first
  /last segment) → a centred **"REPLAY"** callout that fades in only during the cover
  hold (reusing the `Stinger` title-fade pattern, guarded against `holdFrames=0`).
- **`ReplayOverlay.tsx`** — transparent root → `FrameBorder` at fixed
  `FRAME.thickness` → a **REPLAY badge** (dark `ink` pill on the top border, white
  "REPLAY") with a **pulsing dot** via `pulse(frame, period)`. Default position
  top-centre. Composition duration = `TIMING.loopDuration` so the pulse closes its
  cycle and OBS loops seamlessly.

## Studio knobs (Zod, defaults from theme)

- **Stinger:** `bands[]`, `holdFrames`, `settleFrames`, `stagger`, `frameThickness`,
  `label` (default `"REPLAY"`). `coverThickness` is derived (`⌈height/2⌉`), not a knob.
- **Overlay:** `bands[]`, `frameThickness`, `label`.
- Frame-count fields use `.int()`; colour arrays use `.min(1)` (project conventions).

## Testing & verification

Per the owner's call, **no broad unit suite** — graphics are verified visually. The
only automated tests are two invariants visual inspection can't reliably catch:

1. `segmentThickness ≥ height/2` for every colour segment across the cover-hold
   window (silent coverage loss would flash the OBS scene-swap).
2. `pulse(0) === pulse(period)` (a loop seam is intermittent and subtle).

Everything else (frame geometry, eased motion, the look) is verified by:
- rendering `:preview` clips;
- `npx remotion ffprobe <file> | grep alpha_mode` → `alpha_mode : 1`;
- compositing over magenta in a Chromium browser / OBS (ffmpeg CLI drops VP9 alpha);
- eyeballing stills at the key beats (grow / cover / settle / reveal for the stinger;
  a pulse frame or two for the overlay).

## Render scripts

```
render:replay-stinger          remotion render ReplayStinger out/replay-stinger.webm   --codec=vp9 --image-format=png
render:replay-overlay          remotion render ReplayOverlay out/replay-overlay.webm   --codec=vp9 --image-format=png
render:replay-stinger:preview  …same… --scale=0.25
render:replay-overlay:preview  …same… --scale=0.25
```

## OBS wiring (also in README)

- **Stinger:** set as the *Stinger* scene transition between the Live and Replay
  scenes; it serves both directions (transition point ≈ frame 43 / ~720 ms).
- **Overlay:** add `replay-overlay.webm` as a looping media source on the Replay
  scene, layered above the replay footage.

## Out of scope (YAGNI)

- Migrating `Stinger` / `ChaseStinger` onto the theme (possible later).
- Mascot / logo *inside* the replay graphics (the overlay is border + badge + dot
  only); the `public/` assets + theme tokens are wired for future graphics.
- ~~Asymmetric into/out-of-replay clips~~ — *added 2026-06-01:* the recommended
  replay transition is now a directional **chase pair** (`ReplayRewindStinger` in /
  `ReplayResumeStinger` out), reusing `ChaseStinger` via a `reverse` flag. The bars
  `ReplayStinger`/overlay in this spec remain; see `DESIGN_DECISION_DOCUMENT.md`.
- Korean-language label, configurable badge position, configurable pulse speed.
- Sound.

## Notes

Per owner preference, this project uses **no git operations** — spec and code are
saved to disk, not committed. Cross-cutting decisions live in
`DESIGN_DECISION_DOCUMENT.md`; this spec is the detailed design for the replay
graphics specifically.
