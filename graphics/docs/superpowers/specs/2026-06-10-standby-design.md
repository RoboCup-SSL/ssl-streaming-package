# Standby ("next match in …") holding scene — design

**Date:** 2026-06-10
**Status:** approved (verbal), implementing
**Composition id:** `Standby`

## Purpose

A full-screen **opaque** holding graphic shown *between* matches on the RoboCup 2026
SSL broadcast. It displays the DAON mascot, a branded slowly-looping background, and a
baked **"NEXT MATCH IN"** label. The live countdown **number is supplied by OBS** (a Text
source the operator edits, or a countdown plugin) — it is deliberately NOT baked into the
video, because a pre-rendered file cannot know the real seconds remaining.

This is the project's first opaque composition. It is also authored **natively at
1920×1080** (not 3840×2160 + `--scale`), because it is new and its pixel sizes are chosen
for 1080p directly.

## Division of labour (decided during brainstorming)

- Remotion renders the **looping branded background + mascot + fixed label** (the hard-to-
  do-well-in-OBS part).
- OBS overlays only the **live number** on top, in a reserved slot.
- No JSON/HTTP data layer for now (no real schedule endpoint exists). A future OBS Browser
  Source could add live data without changing this composition.

## Visual design

> **Revised 2026-06-11 after review.** Owner feedback, two rounds: (1) make the *colours*
> (not the mascot) carry the motion, a few HUGE bright blocks, **no fades**; then (2) drop
> the scrolling — instead, thick colour bars lined up left→right, tilted ~15°, with a
> **breathing wave** that swells each bar in turn (left→right→left) without pushing the
> others. The v1 drifting-bands + jogakbo-strip + bobbing-mascot below was reworked to this.

Canvas 1920×1080, opaque, `paper #F5F6FE` base. Flat throughout — solid colour, hard
edges, no gradients/opacity/shadows.

- **Tilted breathing bars:** thick vertical `BRAND_BARS` colour bars (one per colour) lined
  up left→right to tile a square field, the whole field **tilted ~15°**. A breathing wave
  breathes left→right, **rests 2 s**, breathes right→left, rests 2 s; the focused colour bulges wider while its neighbours yield
  their facing edge. The bars tile by sliding *shared boundaries* (no overlap, no z-index),
  so every edge moves continuously — this avoids the z-swap "jump" an overlap+z-order version
  produced. No scrolling. This is the scene's slow motion.
- **DAON mascot:** `public/mascot_with_ball.png` (transparent 1024² cutout), placed in the
  right third, **static** (no bob, no drop-shadow).
- **Text block (left-centre):** on a **solid** `paper` panel so the dark type stays legible
  over the bright bands — baked **"NEXT MATCH IN"** label (bold, `ink`), a reserved empty
  number slot with a solid baseline guide so the OBS text lines up, and a baked **"SECONDS"**
  sublabel. No digits are baked in.
- **Wordmark:** white `logo_w.png` inside a small solid `ink` chip top-left.

## Motion & loop

- Seamless loop = **two breaths + two rests**. All timings live in `theme.STANDBY`
  (`STANDBY_BREATH_FRAMES`, `STANDBY_REST_FRAMES`, expressed as seconds × `FPS`); the
  composition's `loopDuration` is **derived** from them — no duration is hardcoded elsewhere.
- **Breathing rhythm:** breathe left→right (eased sweep), hold 2 s at neutral, breathe
  right→left, hold 2 s. Each sweep runs `reach` past the outer bars and uses easeInOut, so
  it starts/ends at zero velocity matching the held rests → smooth AND seam-free.
- **Swell + boundaries:** each bar's swell is a raised-cosine bump (compact support, exactly
  0 beyond `reach` → perfectly neutral rests). Interior boundaries shift by the swell
  *difference* between neighbours (capped below half a bar so they can't cross), outer edges
  pinned → continuous, gap-free, no jump.
- The mascot is static. All motion is a pure function of `useCurrentFrame()` (no
  Date.now/random/timers).

## Components / files

- `src/Standby/standby.ts` — pure math: `breathFocus`, `bandSwell`, and `bandBoundaries`
  (the bars' shared edges).
- `src/Standby/standby.test.ts` — the load-bearing invariants: loop seam, strictly-
  increasing boundaries (no inverted bars), and pinned outer edges (full coverage). Per the
  project's visual-first rule, everything else is verified in Studio + a rendered still.
- `src/Standby/Background.tsx` — paper base + thick vertical colour bars tiling a square
  field tilted by `bandAngle`, widths from `bandBoundaries` (hard edges, no fades, no jump).
- `src/Standby/schema.ts` — Zod props (drives Studio controls); defaults sourced from theme.
- `src/Standby/Standby.tsx` — composition: opaque root `<AbsoluteFill>` WITH
  `backgroundColor` + Background + mascot (`Img`/`staticFile`) + text block + logo chip.
- `src/theme/index.ts` — add a `STANDBY` token block (loopDuration, bandPeriod, bandAngle,
  bandOpacity, mascot/text sizing, accent palette).
- `src/Root.tsx` — register `<Composition id="Standby" />` at 1920×1080, fps 60,
  durationInFrames = STANDBY.loopDuration.
- `package.json` — `render:standby` and `render:standby:preview` scripts (native 1080p, so
  NO `--scale=0.5`; preview may use `--scale=0.5` → 960×540 for a fast check).

## Schema (Studio knobs)

- `label: string` (default "NEXT MATCH IN" — swap to "BACK SOON", "KICKOFF IN", …)
- `sublabel: string` (default "SECONDS"; may be empty)
- `bands: zColor()[] .min(1)` (default `BRAND_BARS` — the huge band colours)
- `loopDuration: int` (derived in `theme.STANDBY` from the breath + rest frames)
- `showSlotGuide: boolean` (default true — the dashed guide box around the number slot)

## Invariant exception (documented)

Unlike every stinger/overlay, this composition is **opaque**: its root `<AbsoluteFill>`
intentionally carries `backgroundColor: paper`. This is correct for a between-matches
holding screen and is NOT the transparency bug. Output is still VP9 WebM for pipeline
consistency (alpha simply unused).

## Testing

- Automated: loop-seam unit test only (matches the project's "pure math is the tested
  layer" + visual-first rules).
- Manual: `npm run dev` (Studio), a rendered still over the loop, and confirm the rendered
  WebM is exactly 1920×1080.

## Out of scope (deferred)

- Live JSON/HTTP data binding (revisit if a schedule API appears).
- Per-league mascot variants / animated mascot (we have the static ball cutout).
- Audio bed.
