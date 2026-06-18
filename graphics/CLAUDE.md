# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A [Remotion](https://www.remotion.dev/) project that renders **transparent (true-alpha) VP9 WebM stinger transitions for OBS**. Videos are React components rendered frame-by-frame; the output drops into OBS as a Stinger scene transition. The owner knows OBS well but is **new to React/Remotion** — favour clear explanations and keep the Studio-driven (no-code) workflow intact.

## Read these first

- **Remotion fundamentals** (frame-based model, `useCurrentFrame`, `interpolate`, `Composition`, `Sequence`, `AbsoluteFill`): https://www.remotion.dev/docs/the-fundamentals and https://www.remotion.dev/docs
- **Transparent video rendering** (the whole point of this project): https://www.remotion.dev/docs/transparent-videos
- **RoboCup SSL vision pattern** (geometry behind the robots in `ChaseStinger`): https://robocup-ssl.github.io/ssl-rules/sslrules.html#_vision
- **Design + plan docs** (the why behind the architecture): `docs/superpowers/specs/` and `docs/superpowers/plans/` — one spec+plan pair per composition.

## Commands

```bash
npm run dev                   # Remotion Studio (browser preview + live prop editing)
npm run test                  # vitest (all tests, run-once)
npx vitest run src/Stinger/wipe.test.ts   # a single test file
npx tsc --noEmit              # type-check (there is no build step; Remotion bundles)
npx remotion compositions     # list registered compositions (sanity check after edits)

npm run render                # Stinger      -> out/stinger.webm        (1080p via --scale=0.5)
npm run render:chase          # ChaseStinger -> out/chase-stinger.webm   (1080p via --scale=0.5)
npm run render:preview        # Stinger,      --scale=0.25 (fast sanity check)
npm run render:chase:preview  # ChaseStinger, --scale=0.25 (fast sanity check)
npm run render:bg             # BreathingBackground -> out/breathing-background.mp4 (H.264, opaque; native 1080p)
npm run render:next-match     # NextMatch    -> out/next-match.png (transparent still block)
npm run render:standby        # Standby      -> out/standby.mp4 (H.264, opaque; native 1080p; combo of the two above)
```

Render a single still for visual checks: `npx remotion still <CompId> out/frame.png --frame=<N> --scale=0.25`.

**Render speed:** `remotion.config.ts` enables GPU rendering (`setChromiumOpenGlRenderer('angle')`) and high `setConcurrency` (cores − 2) for all renders + Studio — this speeds the *rendering* stage. Encoding is separate: the transparent set must use **VP9, whose alpha encoder is CPU-only** (no GPU encoder supports alpha; Remotion hardware-accel is macOS-only). The opaque `Standby` sidesteps this by encoding **H.264** (≈3.5× faster than its VP9 equivalent).

Node 18+ required (currently v22). Remotion packages are pinned to one shared version (`4.0.464`) with an `overrides` block in `package.json` for version compatibility; all `remotion`/`@remotion/*` must stay on the same version.

## Critical invariants

- **Transparency depends on the root `<AbsoluteFill>` having NO `backgroundColor`.** Only the panels/actors carry colour. An opaque full-screen background silently destroys the alpha channel and breaks the stinger. **Exception:** `Standby` is a deliberately *opaque* full-screen holding scene — its root carries `backgroundColor: paper` on purpose. This rule applies to the stingers/overlays only.
- **Verifying alpha:** the rendered WebM reports pixel format `yuv420p` but carries `alpha_mode : 1` (VP9 stores alpha in a per-frame BlockAdditional element). This is correct. The **ffmpeg CLI decoder drops the alpha** (transparent areas render as black in extracted stills), so verify with `npx remotion ffprobe <file> | grep alpha_mode`, or composite the WebM over a bright colour in a **Chromium browser / OBS** (which decode VP9 alpha correctly).
- **OBS coverage:** a stinger must be fully opaque at its "transition point" so OBS can swap scenes unseen. The panel wipe holds full coverage for `holdFrames` around the midpoint. Transition points: **`Stinger` ≈ 750 ms**; **`ChaseStinger` ≈ 830 ms** (its wipe is delayed by `wipeDelay`, shifting the covered moment later).
- Frames are **deterministic functions of `useCurrentFrame()`** — no `Date.now()`, `setInterval`, or random; Remotion renders frames in parallel.

## Architecture

Compositions are registered in `src/Root.tsx` (entry point `src/index.ts` → `registerRoot`). The transition/overlay set (`Stinger`, `ChaseStinger`, `ReplayOverlay`, `ReplayRewindStinger`, `ReplayResumeStinger`) is authored at 3840×2160 @ 60fps, transparent VP9 — the `render:*` scripts emit 1920×1080 via `--scale=0.5` (drop the flag for native 4K). `Standby` is the exception: a full-screen **opaque** "next match in …" holding scene authored **natively at 1920×1080** (no `--scale`) and encoded as **H.264 MP4** (opaque → no alpha → much faster than VP9), a seamless loop whose length is derived in `theme.STANDBY`, with the live countdown number added in OBS.

**Pure math is isolated from rendering and is the only unit-tested layer.** React components that produce pixels are verified observationally (Studio + rendered stills + browser composite), not with unit tests — keep it that way; don't fake pixel tests.

- `src/Stinger/` — the base panel-wipe stinger.
  - `wipe.ts` (pure, tested): `panelOffset()` maps frame → a panel's position across the cover→hold→reveal phases; `offsetToTransform()` maps that to a CSS transform per `direction`; plus `clamp`/`lerp`/`easeInOut`/`interp` helpers reused elsewhere. The `span`/reveal-end math is load-bearing (it guarantees full coverage during the hold and a complete reveal on the last rendered frame) — read its comments before changing.
  - `Panels.tsx` — renders one full-screen coloured `AbsoluteFill` per colour, transformed by the wipe math. Has an optional `windowFrames` prop (falls back to `useVideoConfig().durationInFrames`) so a wipe wrapped in a `<Sequence>` still completes within the shorter window.
  - `Stinger.tsx` — composition: transparent root + `Panels` + optional fading `title`.
  - `schema.ts` / `constants.ts` — Zod props (drives Studio controls; `zColor()` → colour pickers) and dimensions/fps/duration/palette.

- `src/ChaseStinger/` — the base wipe with a top-down RoboCup scene on top (orange ball + robots streaking left→right, "scout" robots driving in before the wipe).
  - `chase.ts` (pure, tested): `actorX()` linear constant-speed position; `laneY()` lane offset + sinusoidal bob. Reuses helpers from `../Stinger/wipe`.
  - `RobotTop.tsx` / `Ball.tsx` — SVG actors. `RobotTop` is the exact SSL vision-pattern geometry (mm units), rotated so the flat front faces the direction of travel.
  - `ChaseLayer.tsx` — positions ball + robots via `chase.ts`. Delay order front→back: scout robots → ball → chasers. `effectiveScouts = min(scouts, robots.length)` guards against the ball being stranded off-timeline.
  - `ChaseStinger.tsx` — composition: transparent root + `Panels` wrapped in `<Sequence from={wipeDelay}>` (the pre-roll that lets scouts enter first) + `ChaseLayer`.
  - `schema.ts` reuses the wipe schema via `stingerSchema.omit({title}).extend({robots, trail, scouts, wipeDelay})`.

- `src/Replay/` — replay-graphics set (`ReplayOverlay`, `ReplayRewindStinger`, `ReplayResumeStinger`); pure looping/jitter math in `frame.ts` (tested for the loop seam). See `docs/superpowers/specs/2026-06-01-replay-graphics-design.md`.

- `src/Standby/` — the opaque between-match holding graphics, split into **reusable pieces stacked in OBS** (`BreathingBackground` + `NextMatch`, plus the `Standby` combo). All native 1920×1080; loop length derived in `theme.STANDBY`. The same two pieces serve both the no-host holding screen and a webcam scene (background behind the cam, block in a corner). See `docs/superpowers/specs/2026-06-11-modular-standby-design.md`.
  - `standby.ts` (pure, tested): `breathFocus()` (4-phase rhythm: breathe across → 2s rest → breathe back → 2s rest, sweeps eased so they glide in/out of the held rests), `bandSwell()` (per-bar raised-cosine swell with compact support, so the rests are perfectly neutral), and `bandBoundaries()` (the bars' shared edges). Bars tile by sliding shared boundaries — NO overlap, NO z-index — so every edge is a continuous function of the frame (this is what killed the earlier z-swap "jump"). Tests assert the loop seam, strictly-increasing boundaries, pinned outer edges, and that the rest phase is neutral.
  - `BreathingBackground.tsx` — composition + reusable component: **opaque** paper base + thick vertical colour bars tiling a square field tilted by `bandAngle`; widths come straight from `bandBoundaries`, so the focused colour bulges wider while neighbours yield their facing edge (hard edges, NO fades, no jumps). Renders standalone → looping MP4 backdrop.
  - `NextMatch.tsx` — exports `NextMatchBlock` (the baked label + reserved OBS number slot + sublabel on a **solid** panel; canvas/position-agnostic, no root background) and the `NextMatch` composition (the block centred on a **transparent** compact 1000×640 canvas → a PNG you place/scale in OBS). Transparency invariant applies here.
  - `Standby.tsx` — the thin **combo** composition: **opaque** root (`backgroundColor: paper`) + `BreathingBackground` + a **static** mascot + logo (holding-screen-only decoration) + `<NextMatchBlock>` positioned left-centre. The countdown number is added in OBS, not baked in. Flat throughout (no shadows/fades).
  - `schema.ts` — `breathingBackgroundSchema` (`bands`, `loopDuration`), `nextMatchSchema` (`label`, `sublabel`, `showSlotGuide`), and `standbySchema` = the two merged; defaults from `theme.STANDBY`.

**To add a new stinger variant:** create `src/<Name>/`, reuse `Stinger/Panels` and `Stinger/wipe` where possible, register a new `<Composition>` in `Root.tsx`, add `render:<name>` scripts, and put the animation logic in a pure tested module mirroring `wipe.ts`/`chase.ts`.

## Live match data (now `../services/obs-live-data/` — Python, separate from Remotion)

A small **Flask** server that auto-fills the on-screen match labels for the broadcast, so the operator never types match info into OBS. **Not** part of the Remotion render pipeline. It used to live in `live/` here; in the monorepo it moved to `../services/obs-live-data/`. See `docs/superpowers/specs/2026-06-16-live-match-data-design.md`.

- The operator edits **one file** (`live/data/schedule.json` → per-field `currentId` pointer); the server hot-reloads it (re-reads on mtime change, serves last-good data if a mid-edit save is invalid). Fully manual — no clock-based auto-advance.
- `live/schedule_logic.py` (pure, **pytest-tested** — the only tested layer): `resolve(data, field, now_dt)` → `{field, division, now, next, secondsUntilNext, countdown}`; `format_countdown` (`M:SS` / `H:MM:SS`, clamp 0). Field A = **Division A**; B0/B1 = **Division B**; group labels/playoff codes repeat across divisions, so matches are keyed by field, never deduped by label.
- `live/app.py` (thin Flask): `GET /field/A|B0|B1`, `/health`; 404 unknown field, 422 bad `currentId`; binds `HOST`/`PORT` (default `0.0.0.0:8000`, `threaded=True`).
- `live/import_schedule.py`: markdown schedule (`# Day` → `## Field` → `### time | label | teamA | teamB`) → `schedule.json`, with built-in round-robin + near-duplicate-name validation (a `CORRECTIONS` map fixes known typos).
- **Delivery to OBS:** the `obs-urlsource` plugin pulls the JSON and renders it in **native OBS text** (no browser source) over the pre-rendered `NextMatch`/background layer. Distributed via OBS scene-collection export — see `live/README.md` for the per-PC checklist.
- Run: `pip install -r live/requirements.txt`, `python live/import_schedule.py`, `PORT=8000 python live/app.py`. Test: `python -m pytest live -v`.

## Conventions

- Schema knobs use integer constraints (`.int()`) for frame-count fields so Studio shows whole-number sliders; arrays that must be non-empty use `.min(1)`.
- The owner has stated **no git operations on this project** — do not commit, branch, or push unless explicitly asked. Save files to disk only.
- `out/` is gitignored render output; clean up scratch verification files (stills, temp HTML) when done.
