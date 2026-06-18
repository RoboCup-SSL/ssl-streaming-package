# Design: Reusable OBS Stinger Template (Remotion)

**Date:** 2026-05-29
**Status:** Approved (pending spec review)

## Goal

Build a Remotion project containing one parameterized `Stinger` composition that
renders a **transparent (true-alpha) WebM** for use as an **OBS Stinger scene
transition**. The animation is a **panel wipe**: colored panels sweep in to fully
cover the screen, hold briefly, then sweep off to reveal the next scene.

The user knows OBS well but is new to React/Remotion. The deliverable must be
usable primarily by tweaking visual knobs in Remotion Studio (via a Zod schema),
not by editing code.

## Output Specs

| Property | Value |
|---|---|
| Resolution | 3840 × 2160 (4K) |
| Frame rate | 60 fps |
| Duration | 90 frames (1.5 s) |
| Codec | VP9 |
| Container | WebM |
| Alpha | Yes — `yuva420p` |

Note: 4K VP9-alpha renders are CPU-heavy and slow. Preview at reduced scale in
Studio; render full 4K only when finalizing.

## Core Architecture — The Wipe Engine

The animation is a pure function of `useCurrentFrame()` (deterministic per frame,
as Remotion requires). The 90-frame timeline has three phases:

| Phase | Frames (approx) | Behavior |
|---|---|---|
| Cover | 0 → 40 | Panels slide from off-screen edge to fully covering the frame |
| Hold | 40 → 50 | Screen 100% covered — OBS swaps scene A → B here |
| Reveal | 50 → 90 | Panels continue off the opposite edge, revealing scene B |

The **hold window** is intentional: it guarantees a few frames of full coverage so
the OBS scene swap is always hidden even if the configured transition point is
slightly off.

Each panel is staggered slightly in time for a layered sweep. Motion is computed
with `interpolate` using an ease-in-out curve.

### Critical: Transparency

The root `AbsoluteFill` has **no background color** — it stays transparent. Only
the panels carry color. This is what makes the alpha channel meaningful. Any
opaque full-screen background would destroy the transparency and break the
stinger.

## Props (Zod Schema)

All props are overridable live in Studio via the auto-generated controls.

| Prop | Type | Default | Purpose |
|---|---|---|---|
| `direction` | `'left' \| 'right' \| 'up' \| 'down'` | `'left'` | Sweep axis/direction (`'left'` = sweeps toward the right) |
| `panelColors` | `string[]` (hex) | tasteful default palette (dark base + accent) | Panel fill colors; array length drives panel count |
| `stagger` | `number` (frames) | `4` | Delay between consecutive panels |
| `holdFrames` | `number` (frames) | `10` | Length of the full-coverage hold window |
| `title` | `string` (optional) | `''` | Optional centered wordmark shown during hold. Empty by default; this is the seam for adding a logo/text layer later without a redesign. |

## Project Structure

```
remotion/
  remotion.config.ts        # png image format + vp9 alpha render defaults
  package.json              # scripts: "dev" (Studio), "render" (alpha webm)
  src/
    index.ts               # registerRoot
    Root.tsx               # registers <Composition id="Stinger">
    Stinger/
      Stinger.tsx          # composition: layers panels + optional title
      Panels.tsx           # the wipe engine
      schema.ts            # zod props + defaults
      constants.ts         # dimensions, palette
```

## Rendering

npm script wrapping:

```
remotion render Stinger out/stinger.webm --codec=vp9 --image-format=png
```

`--image-format=png` preserves alpha through the frame pipeline. VP9 with no
opaque background yields `yuva420p` (a real alpha channel).

## OBS Setup (to be documented in README)

1. Settings → Scene Transitions → **+** → **Stinger**.
2. Video File → `out/stinger.webm`.
3. Transition Point ≈ **750 ms** (middle of the hold window).
4. Apply. Use the transition when switching scenes.

## Verification

- **Studio:** scrub the timeline. Studio renders transparency as a checkerboard,
  so confirm (a) full opaque coverage during the hold phase and (b) genuine
  transparency before/after.
- **Render check:** `ffprobe out/stinger.webm` confirms pixel format carries alpha
  (`yuva420p`); then drop into OBS over a colored scene to confirm the reveal.

## Out of Scope (YAGNI)

- Logo/image layer (seam left via `title` prop; add later if needed).
- Track-matte MP4 output (chose true-alpha WebM).
- Additional motion concepts (slice/geometric) — possible future second composition.
- Audio for the stinger.
```

