# Handoff — RoboCup 2026 replay graphics (for a fresh Claude Code instance)

You are picking up a Remotion project mid-stream. This file is a transcript/summary of
the work done in a prior session (on another machine) so you have full context. **Read
`CLAUDE.md` and `DESIGN_DECISION_DOCUMENT.md` first — they are the canonical sources of
truth; this file is the narrative + current state.**

## What this project is

A [Remotion](https://www.remotion.dev/) project that renders **transparent (true-alpha)
VP9 WebM broadcast graphics for OBS** — scene-transition "stingers" and frame overlays —
for streaming the **RoboCup 2026 Small Size League (SSL)**. Output drops into OBS.
The owner knows OBS well but is **new to React/Remotion** — favour clear explanations and
keep the Studio-driven (no-code) workflow intact.

Event facts: RoboCup 2026, Songdo ConvensiA, **Incheon, South Korea, July 2–6 2026**.
SSL = robot soccer; teams are **blue or yellow**, orange ball; Division A = 11v11,
Division B = 6v6. The official brand uses a **5-colour motif** (see palette below).

## Standing rules (do not violate)

- **No git operations** on this project — save to disk only; never commit/branch/push
  unless explicitly asked.
- **Transparency invariant:** the root `<AbsoluteFill>` carries NO `backgroundColor`;
  only graphic elements have colour, or the VP9 alpha channel is destroyed.
- **OBS coverage invariant:** a stinger must be fully opaque at its transition point so
  OBS can swap scenes unseen.
- **Determinism:** every frame is a pure function of `useCurrentFrame()` — no `Date.now()`,
  `Math.random()`, or timers (frames render in parallel).
- **Visual-first testing (owner's call):** this departs from the older "pure math is the
  only tested layer" note in CLAUDE.md. For the replay work we keep only TWO automated
  tests (coverage invariant + loop seam); everything else is verified visually. Don't add
  broad unit tests for the replay graphics.
- **Central theme is the single source of truth:** every stinger/frame imports colours,
  sizes, timings from `src/theme/index.ts`. Studio Zod knobs still exist, but their
  *defaults* come from the theme. Tune the theme + re-render to re-theme everything.

## Brand palette (in `src/theme/index.ts`, sampled from 2026.robocup.org)

`orange #F26223 · green #55B748 · lime #CDDC29 · purple #804FA0 · magenta #E63D66`,
plus `paper #F5F6FE` (bg) and `ink #1a1a1e` (text). `BRAND_BARS` is the ordered 5-colour
motif (the brand hook). SSL team colours (blue/yellow) are a SEPARATE concern — don't
conflate them with the brand palette. Assets in `public/`: `mascot_with_ball.png`
(official cream-robot mascot), `logo_w.png` (wordmark).

## What was built this session

Starting point: two compositions existed — `Stinger` (panel-wipe) and `ChaseStinger`
(robots chasing a ball over the wipe). The owner scoped the project up to a real SSL
broadcast package and asked for **replay graphics**.

Delivered (compositions authored at 3840×2160 @ 60fps, transparent VP9; **render
output is 1920×1080** via `--scale=0.5` on the `render:*` scripts — see Commands):

1. **`ReplayStinger`** — a "painting-frame" scene transition. Top & bottom bars split
   into 5 equal-width colour segments (20% each, left→right); full-height orange left
   edge + magenta right edge; hollow centre. Transition: the striped bars grow inward and
   **meet** to cover the screen as 5 vertical stripes (OBS swap, arriving left→right via a
   `stagger`), then part and settle into the thin frame, then clear. `coverThickness =
   ⌈height/2⌉`. Kept as a generic symmetric option (no longer the replay default — see #4/#5).
2. **`ReplayOverlay`** — a seamlessly **looping** frame overlay (the same 5-colour frame +
   a "REPLAY" pill badge + pulsing dot). Loops cleanly (pulse period divides loop length).
   Sits on the replay footage in OBS, set to loop.
3. The replay transition became a **directional chase pair** (owner's idea: a replay is a
   rewind):
   - **`ReplayRewindStinger`** (live → replay) — reuses `ChaseStinger` with a new optional
     `reverse` flag (robots roll **right→left while facing right** = "driving backwards"),
     brand-recoloured wipe, **plus a VHS tape-shuttle FX overlay** (`RewindFX`): scanlines,
     a vertically-rolling tracking bar, horizontal tape-jitter, and a blinking ◄◄ REWIND
     glyph. The jittered chase is **overscanned ×1.03** so jitter never exposes a
     transparent edge during the coverage hold.
   - **`ReplayResumeStinger`** (replay → live) — the same chase driving **forward
     left→right** (a "resume"), brand-recoloured.

Why the rewind FX: direction reversal alone didn't read — at speed the near-symmetric
robots just looked like normal driving. The ◄◄ REWIND glyph + VHS texture carry the
meaning regardless of robot orientation.

### Files (created/modified this session)

- `src/theme/index.ts` — NEW tokens: `CANVAS, FPS, BRAND, BRAND_BARS, FRAME, TIMING,
  REWIND, ASSETS, EASING`.
- `src/Replay/` — NEW: `frame.ts` (pure: `replayThickness`, `segmentThickness`, `pulse`,
  `hashNoise`, `jitterX`, `trackingBarY`), `frame.test.ts` (the 2 tests), `schema.ts`,
  `FrameBorder.tsx`, `ReplayStinger.tsx`, `ReplayOverlay.tsx`, `RewindFX.tsx`,
  `ReplayRewindStinger.tsx`.
- `src/ChaseStinger/` — MODIFIED (non-breaking): added optional `reverse` to `chase.ts`
  (`actorX`), `ChaseLayer.tsx`, `ChaseStinger.tsx`, `schema.ts` (`reverse: z.boolean().optional()`).
- `src/Root.tsx` — MODIFIED: registers `ReplayStinger`, `ReplayOverlay`,
  `ReplayRewindStinger`, `ReplayResumeStinger`; `reverse:false` added to the existing
  `ChaseStinger` defaultProps.
- `package.json` — MODIFIED: `render:replay-*` scripts. Lockfile was regenerated against
  public npm (see Environment).
- `README.md` — MODIFIED: replay sections + OBS wiring.
- `DESIGN_DECISION_DOCUMENT.md` (repo root) — NEW living decision log with dated entries.
- `docs/superpowers/specs/2026-06-01-replay-graphics-design.md`, 
  `docs/superpowers/plans/2026-06-01-replay-graphics.md` — NEW spec + plan.
- `public/` — NEW: mascot + logo.

### Verification status (as of handoff)

`npx tsc --noEmit` clean; `npm run test` = **26/26 pass**; all rendered webms report
`alpha_mode : 1`; cover frames verified fully opaque (alpha 255) including edges. Renders
live in `out/` (10 webms; the replay deliverables are `replay-rewind.webm`,
`replay-resume.webm`, `replay-overlay.webm`, `replay-stinger.webm`).

## OBS wiring (recommended)

- Live → Replay transition = `out/replay-rewind.webm`
- Replay → Live transition = `out/replay-resume.webm`
- During replay: `out/replay-overlay.webm` as a media source on the Replay scene, **set to
  loop**, above the footage.
(`replay-stinger.webm` is a generic symmetric alternative.)

## Commands

```bash
npm run dev                          # Remotion Studio (live prop editing)
npm run test                         # vitest (26 tests)
npx tsc --noEmit                     # type-check (use ./node_modules/.bin/tsc if npx grabs the wrong one)
npx remotion compositions            # list all 6 compositions
npm run render:replay-rewind         # 1080p -> out/replay-rewind.webm   (+ :preview at 960x540)
npm run render:replay-resume         # 4K -> out/replay-resume.webm
npm run render:replay-overlay        # 4K -> out/replay-overlay.webm  (loop in OBS)
npm run render:replay-stinger        # 4K -> out/replay-stinger.webm
# also: render, render:preview (Stinger); render:chase[:preview] (ChaseStinger)
```

Verify alpha: `npx remotion ffprobe <file> 2>&1 | grep alpha_mode` → `alpha_mode : 1`.
NOTE: the ffmpeg CLI decoder DROPS VP9 alpha (transparent areas look black in extracted
stills). To eyeball, composite the WebM over a bright colour in a Chromium browser / OBS,
or render a still PNG and alpha-composite it over a colour (PIL) before viewing.

## Environment gotchas (IMPORTANT on this Desktop machine)

- **This machine likely has no `node_modules` yet** — they were excluded from the
  transfer. Run `npm install` first.
- **Node is/was NOT installed on this Desktop** at handoff time. Install **Node 18+**
  (the prior machine used v20) before `npm install`.
- If `npm install` fails, try deleting `package-lock.json` and reinstalling.
- First render downloads the **Chrome headless shell (~92 MB)** — needs internet.
- Remotion packages are pinned to one shared version (`4.0.464`) with an `overrides` block
  in `package.json`; keep all `remotion`/`@remotion/*` on the same version.

## Open / optional next steps discussed (NOT done — offer or wait for direction)

- Tune the VHS rewind feel via `theme.REWIND`: `scanlineOpacity` (0.22), `jitter` (10px),
  `barSpeed`/`barHeight`.
- Optional: a down-counting **timecode** next to the ◄◄ REWIND glyph.
- Tune the frame: `FRAME.thickness` (120 → chunkier), L→R sweep `stagger` (4).
- Possible: have the ball clearly **lead** the rewind; fewer robots for a cleaner read.
- Possible (deferred): migrate the original `Stinger`/`ChaseStinger` onto `src/theme`.
- More stingers/overlays will follow (scoreboards, lower-thirds) — all should pull from
  `src/theme` and follow the same brand.

## Note on memory

The prior session saved project memories (brand scope, palette, npm-registry fix) under
the *other* machine's `~/.claude`. Those will NOT be present here — the facts you need are
captured in this file, `CLAUDE.md`, and `DESIGN_DECISION_DOCUMENT.md`.
