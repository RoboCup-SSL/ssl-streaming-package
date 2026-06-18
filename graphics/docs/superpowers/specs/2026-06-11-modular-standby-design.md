# Modular standby — reusable breathing background + next-match block — design

**Date:** 2026-06-11
**Status:** approved (verbal), implementing
**Composition ids:** `BreathingBackground`, `NextMatch`, `Standby` (rebuilt)

## Purpose

Refactor the single baked `Standby` holding scene into **independent, reusable, pre-rendered
sources** the operator stacks in OBS — driven by a stream-day need for more than one scene:

- **08:00–08:50** — no host yet → full-screen holding scene (background + "next match in" + number).
- **08:50–09:00** — host on webcam → the *same* breathing background behind the webcam, with a
  *small* "next match in" block tucked in a corner over the cam.

Both scenes want the same two visual elements at different sizes, so we split them into two
sources that each render to their own file and compose live in OBS. Runtime cost is negligible
(pre-rendered files; the stream PCs are GTX 4060 + strong CPU — layering a couple of decoded
files plus a PNG is trivial). OBS never composites anything heavy; it plays what's already baked.

## What changes

The existing `Standby` is split into two reusable pieces; a thin `Standby` combo is kept:

| Composition | What it is | Renders to | Format |
|---|---|---|---|
| `BreathingBackground` | The tilted breathing colour-bars **only** (opaque, full-screen, seamless loop). Nothing on top. | `out/breathing-background.mp4` | H.264 loop (opaque = fast) |
| `NextMatch` | A **compact, transparent** block: "NEXT MATCH IN" label + reserved countdown-number slot + optional sublabel. No motion. | `out/next-match.png` | single transparent PNG |
| `Standby` | Thin combo: opaque root stacking `BreathingBackground` + logo + mascot + the next-match block at holding-screen position. | `out/standby.mp4` | H.264 loop |

This is the standard Remotion pattern: `BreathingBackground` and `NextMatch` are React
**components**, each *also* registered as its own `<Composition>` so it renders standalone, and
`Standby` renders the same components stacked. **One source of truth, three output files.** No
duplicated markup, no duplicated animation logic.

## Division of labour (Remotion vs OBS)

- Remotion renders the **looping branded background** and the **fixed label/slot block** (the
  parts that are hard to do well in OBS).
- OBS supplies the **live countdown number** on top of the reserved slot (a Text source the
  operator edits, or a countdown plugin) — never baked, because a pre-rendered file can't know
  the real seconds remaining. Unchanged from the original Standby.
- OBS also does all **layering and placement** (webcam over background, block into a corner).
  No composition needs to know where the webcam goes.

## Component boundaries

- **`BreathingBackground` component** — the current `Background.tsx`, unchanged in behaviour:
  thick vertical `BRAND_BARS` bars tiling a tilted square field, breathing wave from
  `standby.ts` (`bandBoundaries`), opaque `paper` root. Promoted to its own composition.
- **`NextMatchBlock` component** (new, extracted from `Standby.tsx`) — *just* the solid-paper
  panel with the uppercase `label`, the reserved number slot (dashed guide + orange baseline),
  and the optional `sublabel`. **Canvas-agnostic and position-agnostic**: it renders the block
  and nothing else, no root background. Each composition sizes/places it:
  - `NextMatch` composition → a **compact transparent canvas** (~640×620, tunable) with the
    block centred. Renders to the standalone PNG you drop anywhere and scale/move in OBS.
  - `Standby` composition → renders `<NextMatchBlock/>` inside a positioned absolute wrapper at
    the holding-screen spot (left-centre, as today).
- **Logo chip + mascot** stay **holding-screen decoration** defined inline in the `Standby`
  combo only — deliberately *not* part of `NextMatchBlock` (you don't want the big mascot in a
  webcam corner). If the operator wants the logo on the webcam scene, OBS can add the static
  `logo_w.png` directly.

## Files

```
src/Standby/
  standby.ts            # pure breathing math — UNCHANGED (still the only tested layer)
  standby.test.ts       # UNCHANGED
  BreathingBackground.tsx   # renamed from Background.tsx; component renamed Background -> BreathingBackground
  NextMatch.tsx         # NEW — exports NextMatchBlock (the block) + the compact NextMatch composition body
  Standby.tsx           # rebuilt — opaque root: BreathingBackground + logo + mascot + <NextMatchBlock/>
  schema.ts             # split into three schemas (below)
```

`src/Root.tsx` registers all three compositions. `package.json` gains `render:bg` /
`render:next-match` scripts; `render:standby` stays (now assembled from the modular pieces).

## Schema (Studio knobs)

Split the current `standbySchema` so each piece exposes only what it needs, then compose:

```ts
breathingBackgroundSchema = { bands, loopDuration }
nextMatchSchema           = { label, sublabel, showSlotGuide }
standbySchema             = breathingBackgroundSchema.merge(nextMatchSchema)   // unchanged surface
```

Defaults come from `theme` exactly as today (`BRAND_BARS`, `STANDBY.loopDuration`, etc.). The
`Standby` Studio surface is unchanged, so nothing the operator already knows breaks.

## Dimensions / duration / format

- `BreathingBackground` — 1920×1080, opaque, `durationInFrames = STANDBY.loopDuration`,
  H.264 MP4 loop. (Authored natively at 1080p, like Standby — no `--scale`.)
- `NextMatch` — compact transparent canvas (~640×620), `durationInFrames = 1` (no motion),
  rendered with `remotion still` → transparent PNG. Transparency invariant **applies** here
  (root carries no `backgroundColor`; only the inner panel is solid `paper`).
- `Standby` — 1920×1080, opaque, `durationInFrames = STANDBY.loopDuration`, H.264 MP4 loop.

## Render scripts

```bash
npm run render:bg               # BreathingBackground -> out/breathing-background.mp4 (loop in OBS)
npm run render:bg:preview       # --scale=0.5 sanity check
npm run render:next-match       # remotion still NextMatch out/next-match.png --frame=0
npm run render:standby          # Standby -> out/standby.mp4 (unchanged id; combined holding screen)
npm run render:standby:preview  # unchanged
```

## OBS usage

- **Holding scene (no host):** play `out/standby.mp4` (one looping video) + an OBS Text source
  over the slot for the live number. Lowest possible load. *(Or, if you prefer, layer
  `breathing-background.mp4` + `next-match.png` + text manually — same result, more flexible.)*
- **Webcam scene (host talking):** `breathing-background.mp4` (full-screen backdrop, looped) →
  webcam source on top, sized a bit smaller so the bars breathe around its edges (the bars
  *become* the border — no dedicated frame graphic needed) → `next-match.png` scaled into a
  corner → OBS Text source for the number over its slot.

## Invariants

- `BreathingBackground` and `Standby` are **opaque** (root carries `backgroundColor: paper`) —
  the documented exception to the project's transparency invariant, same as the original
  Standby. `NextMatch` is **transparent** and **follows** the invariant (transparent root, solid
  panel only on the inner block).
- Determinism unchanged: all motion is `bandBoundaries(useCurrentFrame())`; no `Date.now`/random.

## Testing

No new pure math — `standby.ts` and its tests are untouched, so the existing loop-seam /
boundary invariants still cover the only testable layer. The three components are verified
visually (Studio + rendered files + OBS composite), per the project's visual-first convention.
Sanity check after the refactor: `npx remotion compositions` lists all three; the rebuilt
`Standby` is visually identical to the pre-refactor version (same elements, same positions).

## Out of scope (deferred)

- **No dedicated webcam border/frame composition** — the breathing background showing around a
  smaller webcam source replaces it. Revisit only if the operator wants a frame *without* the
  background.
- **No live schedule data layer** (HTTP/JSON) — the number stays an OBS Text source, as today.
- **No motion on `NextMatch`** — it's a static PNG. If a subtle pulse is ever wanted, it
  becomes a looping VP9 WebM instead; not now.
