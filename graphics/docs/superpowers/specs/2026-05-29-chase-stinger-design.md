# Design: ChaseStinger — RoboCup bots chasing a ball over the stinger

**Date:** 2026-05-29
**Status:** Approved (pending spec review)

## Goal

A new Remotion composition, `ChaseStinger`, that adds a top-down RoboCup SSL
scene on top of the existing panel-wipe stinger: an orange ball streaks left→right
across the screen with three robots chasing it. The panel wipe is retained so the
output still works as a real OBS Stinger transition (full coverage + scene swap at
the hold window). Output stays a transparent 4K/60fps/90-frame VP9 WebM.

The user knows OBS, not React; all creative knobs are exposed in Remotion Studio
via a Zod schema.

## Choreography (Approach A — continuous streak)

All actors sweep left→right across the full 1.5 s, timed so the pack crosses
screen-centre during the hold window (frames 40–50), where the opaque panels act
as a spotlight. Over the transparent cover/reveal phases the actors briefly
overlay the live scene; during the hold they pop against the solid panel colour.

- **Ball** leads (enters from the left first, exits right first).
- **Three robots** chase behind at staggered horizontal offsets, in slightly
  different vertical "lanes", each with a gentle vertical bob for life.
- Robots face their direction of travel: the flat front points **right**.

## Robot roster

Two blue-team + one yellow-team robot (team colour = the centre dot), each with a
distinct four-dot ID pattern drawn from the SSL marker palette (green / magenta).

## Geometry (reused, to scale, 1 unit = 1 mm)

Top-down robot, from the verified SSL spec:
- Body: circle R85, front cut flat by a chord at 55 mm (corners at x = ±64.807).
- Centre dot: r25 (Ø50), team colour.
- Four ID dots: r20 (Ø40) at radius 65 mm — front pair wide (±54.772, +35),
  rear pair narrow (±35, −54.772) relative to the robot's own front.
- Body fill: dark matte (#1a1a1e-ish), matching the "black/dark grey matte" rule.

Ball: orange disc (~SSL orange) with a soft highlight so it reads as a sphere,
sized in proportion to the robots (real SSL ball ≈ 43 mm vs robot ≈ 180 mm).

## Architecture

New folder `src/ChaseStinger/`, reusing `src/Stinger/Panels.tsx`, `wipe.ts`, and
`constants.ts`. Registered as a second `<Composition id="ChaseStinger">` in
`src/Root.tsx`. The existing `Stinger` composition is untouched.

Files:
- `src/ChaseStinger/chase.ts` — pure math (no React/Remotion imports). `actorX()`
  maps frame → horizontal position for an actor given its start delay and travel
  span (off-left → off-right, monotonic). Helpers for lane y-offset and bob. Mirrors
  the `wipe.ts` pure-function pattern. **Unit-tested.**
- `src/ChaseStinger/RobotTop.tsx` — top-down robot as inline SVG/divs. Props:
  `teamColor: string`, `idDots: [string, string, string, string]`. Rotated so the
  flat front faces right.
- `src/ChaseStinger/Ball.tsx` — orange ball with highlight.
- `src/ChaseStinger/ChaseLayer.tsx` — renders the ball + 3 robots, positioning each
  via `chase.ts` + `useCurrentFrame()`/`useVideoConfig()`.
- `src/ChaseStinger/ChaseStinger.tsx` — composition root: transparent
  `<AbsoluteFill>` (no background) → `<Panels>` (reused wipe) → `<ChaseLayer>`.
- `src/ChaseStinger/schema.ts` — Zod props: the wipe knobs
  (direction/panelColors/stagger/holdFrames/title) plus a `robots` array (team
  colour + 4 ID dot colours per robot) and `trail` (integer frames each robot lags
  behind the ball — robot _i_ lags `(i+1) * trail` frames, so they string out behind it).

Layer order matters: panels first (cover), chase on top (hero). Root stays
transparent so VP9 alpha is preserved.

## Studio knobs (Zod schema)

- Existing wipe knobs: `direction`, `panelColors`, `stagger`, `holdFrames`, `title`.
- `robots`: array of `{teamColor, idDots: [c1,c2,c3,c4]}` (default: 2 blue, 1 yellow,
  distinct IDs). Length drives how many bots chase.
- `trail`: integer frames of lag between the ball and each successive robot.

## Verification

- Unit tests for `chase.ts` (actor enters off-left, exits off-right, monotonic;
  ball leads the robots; lane/bob bounded).
- Render stills at several frames (e.g. 10/30/45/60/80); composite the rendered
  webm over magenta in a Chromium browser to confirm the chase reads clearly and
  the alpha channel survives (same method used for the base stinger).
- `npx remotion compositions` lists both `Stinger` and `ChaseStinger`.

## Out of scope (YAGNI)

- Ball "catch"/collision beat (Approach C).
- Speed-lines / motion trails (could add later).
- Wheels or 3-D robot rendering — top-down flat shapes only.
- Configurable chase direction — fixed left→right (matches the default rightward wipe).
- Sound.

## Notes

Per user preference, this project uses **no git operations**; the spec and code are
saved to disk but not committed.
