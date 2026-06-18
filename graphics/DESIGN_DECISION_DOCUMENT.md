# Design Decision Document

A living record of the cross-cutting decisions behind this project's broadcast
graphics, so we don't re-litigate the same questions each time a new stinger or
frame is added. Per-feature detail lives in `docs/superpowers/specs/`; the "how it
works" lives in `CLAUDE.md`. **This file is the "why" and the standing rules.**

Append a dated entry whenever a decision is made or changed. Keep entries short:
decision, rationale, status.

---

## North star

A reusable package of **transparent (true-alpha) VP9 WebM broadcast graphics** —
stingers (scene transitions) and frames/overlays — for streaming the **RoboCup 2026
Small Size League (SSL)** in OBS. Event: Songdo ConvensiA, Incheon, Republic of
Korea, July 2–6 2026. More stingers and frames will follow; everything must share
one consistent theme (logos, colours, timing, "vibe").

## Brand tokens (RoboCup 2026)

Sampled from 2026.robocup.org assets on 2026-06-01. **Source of truth in code:
`src/theme/`** — do not hardcode these anywhere else.

| Token | Value |
|---|---|
| Orange | `#F26223` |
| Green | `#55B748` |
| Lime | `#CDDC29` |
| Purple | `#804FA0` |
| Magenta | `#E63D66` |
| Paper (bg motif) | `#F5F6FE` |
| Ink (text/body) | `#1a1a1e` |

- **Signature motif:** the ordered 5-colour bar set `[orange, green, lime, purple,
  magenta]` (the site's "5pattern" divider). This is THE brand hook — graphics built
  from it read instantly as RoboCup 2026.
- **Assets:** `assets/mascot_with_ball.png` (cream robot mascot in hanbok, kicking a
  ball, transparent bg); RoboCup 2026 wordmark `logo_w.png`. Remotion serves images
  from `public/`, so theme asset tokens assume images are copied there.
- **SSL team colours are blue / yellow** — a *separate* concern from this brand
  palette. Do not conflate team identity with brand theme.

## Standing conventions

- **Central theme is the single source of truth.** Every stinger/frame imports
  colours, thickness, timings, easing, and asset paths from `src/theme/`. Studio
  Zod knobs still exist per composition, but their *defaults* come from the theme.
  Tuning the theme + re-rendering re-themes everything.
- **Transparency invariant:** the root `<AbsoluteFill>` carries NO `backgroundColor`;
  only the graphic's elements have colour. An opaque background silently destroys the
  VP9 alpha channel. (See `CLAUDE.md`.)
- **OBS coverage invariant:** a stinger must be fully opaque at its transition point
  so OBS can swap scenes unseen.
- **Determinism:** every frame is a pure function of `useCurrentFrame()` — no
  `Date.now()`, randomness, or timers.
- **No git operations** on this project — save to disk only; never commit/branch/push
  unless explicitly asked.
- **Alpha verification:** rendered WebM reports `yuv420p` but carries `alpha_mode : 1`;
  verify with `npx remotion ffprobe <file> | grep alpha_mode` or composite over a
  bright colour in Chromium / OBS (the ffmpeg CLI drops VP9 alpha).

## Decisions log

### 2026-06-01 — Project scope: SSL broadcast graphics package
The project grows from a generic stinger toy into a themed broadcast-graphics package
for RoboCup 2026 SSL: stingers **and** static/looping overlays. *Status: active.*

### 2026-06-01 — Brand source = 2026.robocup.org
Colours, motif, mascot, and wordmark are taken from the official site (tokens above).
Rationale: the broadcast should match the event's official identity. *Status: active.*

### 2026-06-01 — Replay flow: stinger both ways, frame during
Replay uses a stinger transition **into and out of** replay, with a frame overlay
shown on the replay footage the whole time. Rationale: matches the intended OBS
operator workflow. *Status: active.*

### 2026-06-01 — Replay overlay = seamlessly looping WebM
The overlay is a looping transparent WebM (not a static PNG), because a replay runs
for an arbitrary length and a one-shot clip can't cover it. Its only motion is a
pulsing dot, sized so the loop closes with no visible seam. *Status: active.*

### 2026-06-01 — Frame style = sleek 5-colour brand border
The "painting frame" is a clean modern border built from the 5-colour brand motif
(not an ornate gilded museum frame). Rationale: instantly on-brand, crisp on a busy
SSL field. *Status: active.*

### 2026-06-01 — Replay overlay content = border + REPLAY badge + pulsing dot
No mascot or wordmark on the replay overlay (kept minimal). English `"REPLAY"` label.
*Status: active.*

### 2026-06-01 — Replay stinger = bars-form-the-frame via one animated-thickness border
Chosen over a plain recoloured wipe or a recoloured ChaseStinger. Implemented as a
single 5-colour `FrameBorder` whose **total thickness is animated**: grow to full
coverage (OBS swap) → settle at the thin frame thickness (momentarily identical to
the overlay) → clear. One symmetric clip serves both directions. Rationale: the
transition literally resolves into the overlay's look; one shared component
guarantees they match; full coverage at the hold preserves the OBS invariant.
*Status: active.*

### 2026-06-01 — Central theme module (`src/theme/`)
All graphics import tokens (palette, motif, thickness, timings, easing, assets) from
one module; per-composition Studio defaults derive from it. Rationale: tune once,
apply everywhere; required as the package grows. *Status: active.*

### 2026-06-01 — Testing: visual-first, with two targeted invariant tests
Override of the `CLAUDE.md` "pure math is the only unit-tested layer" convention
**for the replay graphics**: the owner verifies visually. We keep ONLY two automated
tests — both for invariants the eye can't reliably catch:
(1) stinger thickness `≥ width/2` across the whole cover-hold (silent coverage loss
flashes the OBS swap); (2) `pulse(0) === pulse(period)` (loop seam is intermittent).
Everything else is verified by render + ffprobe + browser/OBS composite. Rationale:
test what visual inspection misses; don't test what it catches. *Status: active.*

### 2026-06-01 — Border redesign: left→right 5-colour bars (supersedes the concentric-ring frame)
The frame is no longer concentric rings. New geometry: the **top and bottom bars**
are each split into 5 equal-width colour segments (20% each), coloured left→right
(orange, green, lime, purple, magenta); the **left edge** is a full-height orange
bar and the **right edge** a full-height magenta bar. Hollow centre.
Transition: the striped top/bottom bars **grow inward and meet in the middle**,
arriving **left→right** (a per-segment `stagger`, orange first), so the covered
moment is 5 clean vertical stripes; then they part, settle into the thin striped
frame (== overlay), and clear. Because coverage now happens when top+bottom meet,
`coverThickness = ⌈height/2⌉` (was width/2). Pure math: `segmentThickness()` (grow,
staggered) + `replayThickness()` (settle/reveal + side bars). Rationale: the user
wants the 5 colours read left→right across the screen; this also gives a more
striking, on-identity sweep. *Status: active. Supersedes the "sleek 5-colour brand
border" and the concentric-ring detail of the "bars-form-the-frame" entries above.*

### 2026-06-01 — Replay transition is a directional chase pair (rewind in / resume out)
Replaces the single-symmetric-clip plan for the *replay scene-transition*. Two clips,
both reusing the `ChaseStinger` machinery brand-recoloured (panel wipe = `BRAND_BARS`):
- **`ReplayRewindStinger`** (live→replay): robots + ball travel **right→left while
  still facing right** — they read as "driving backwards", i.e. the play rewinding.
  Wipe direction `left`.
- **`ReplayResumeStinger`** (replay→live): robots drive **forward left→right** (the
  normal chase) — the play resuming. Wipe direction `right`.
Implemented via a new **optional `reverse` flag** on the chase machinery
(`actorX` swaps its start/end x; threaded through `ChaseLayer`/`ChaseStinger`;
`reverse: z.boolean().optional()` so the existing `ChaseStinger` composition and its
test are unaffected — undefined = forward). Robots always face right (RobotTop
unchanged); only travel direction flips.
Rationale: a replay is a rewind — reversing the robots sells it instantly, and reusing
the existing stinger was the user's explicit suggestion. The bars `ReplayStinger` is
**kept but demoted** (available, no longer the replay default); `ReplayOverlay` (the
looping frame) is unchanged and still shown during the replay. *Status: active.
Supersedes the "one symmetric clip" choice for the replay transition.*

### 2026-06-01 — Rewind needs an FX overlay (direction reversal alone didn't read)
Reversing the robots wasn't enough — at speed they're near-symmetric, so it just
looked like normal driving. Added a **VHS tape-shuttle FX overlay** on the rewind
clip (`RewindFX` + a `ReplayRewindStinger` wrapper): horizontal **scanlines**, a
vertically **rolling tracking bar**, deterministic horizontal **tape-jitter**, and a
blinking **◄◄ REWIND glyph**. The glyph carries the meaning unambiguously regardless
of robot orientation; the tape texture sells "rewinding". The jittered chase is
**overscanned (`REWIND.overscan` = 1.03)** so jitter can never expose a transparent
edge during the coverage hold (verified: cover frame alpha 255 to the edges). Tokens
in `theme.REWIND`; pure helpers `hashNoise`/`jitterX`/`trackingBarY` (deterministic —
no `Math.random`). *Status: active.*

### 2026-06-02 — Render output is 1080p via --scale=0.5 (compositions stay 4K)
Owner wants 1920×1080 output. Rather than re-author every absolute-px value (frame
thickness, fonts, robot/ball sizes, scanlines, jitter — all tuned for 3840×2160), the
`render:*` scripts add `--scale=0.5` so the 4K compositions render at exactly
1920×1080 with identical proportions (also faster, trivially reversible). Compositions
remain authored at 3840×2160; `:preview` stays `--scale=0.25`. All six full-res
outputs re-rendered at 1080p, `alpha_mode : 1` verified. *Status: active.*

### 2026-06-11 — Removed `ReplayStinger` (the directional rewind/resume pair fully replaces it)
Deleted the symmetric bars-meet-in-the-middle replay transition. The directional pair
(`ReplayRewindStinger` live→replay, `ReplayResumeStinger` replay→live) covers the replay
transition completely, and OBS sets a different Stinger per scene-change direction, so the
single symmetric clip wasn't earning its keep — the VHS rewind FX reads far better than a
direction-agnostic bar wipe. Removed: `ReplayStinger.tsx`, `replayStingerSchema`, the
`segmentThickness`/`replayThickness` pure helpers + their coverage test, the Root
registration, and both `render:replay-stinger` scripts. **Kept** (still used by
`ReplayOverlay`): `FrameBorder` and `pulse()`. This supersedes the "kept but demoted" status
the bars stinger had under the 2026-06-01 directional-pair decision. *Status: active.*

### 2026-06-11 — Standby split into reusable pieces (`BreathingBackground` + `NextMatch`)
The single baked `Standby` was refactored into modular, independently-rendered sources the
operator stacks in OBS, driven by a stream-day need for two scenes (no-host holding screen
*and* a host-on-webcam scene) that want the same elements at different sizes:
- **`BreathingBackground`** — the tilted breathing colour-bars alone (opaque, looping MP4).
  Reusable backdrop: full-screen holding screen, or behind a webcam (the bars showing around a
  smaller webcam source *become* the border — so **no dedicated webcam-frame graphic** is built).
- **`NextMatch`** — the "NEXT MATCH IN" label + reserved number slot, a compact **transparent**
  block (PNG), positioned/scaled freely in OBS. Number still OBS-supplied.
- **`Standby`** — kept, rebuilt as a thin combo stacking the two (+ mascot/logo, which stay
  holding-screen-only decoration). Verified visually identical to the pre-refactor render.
In code: `BreathingBackground`/`NextMatchBlock` are components each also registered as their
own `<Composition>`; `standby.ts` math and its tests are untouched. Schema split into
`breathingBackgroundSchema` + `nextMatchSchema`, merged for `standbySchema`. Rationale: reuse
in code + pre-rendered files in OBS (negligible runtime cost on the GTX 4060 stream PCs). Spec:
`docs/superpowers/specs/2026-06-11-modular-standby-design.md`. *Status: active. Refines the
2026-06-10 Standby design.*

### 2026-06-11 — Signature look = big bold brand-colour blocks, in motif order
The `Standby` background landed the look the owner wants as the package's **recurring
visual signature**: the 5 brand colours rendered as **big, bold, full-bleed blocks**
(thick bars/panels — not thin accents), always in the motif order **orange → green →
lime → purple → magenta** (`BRAND_BARS`), with **hard edges and no fades**. New
graphics should lean on this bold-block treatment (large areas of flat brand colour in
that order) rather than small/decorative uses of the palette. Rationale: it's the
strongest, most instantly-RoboCup-2026 expression of the motif and the owner explicitly
likes it. *Status: active. Applies going forward; existing pieces adopt it as convenient
(see the un-migrated note below).*

### 2026-06-01 — Existing Stinger / ChaseStinger left un-migrated
They keep their own palettes for now; the theme module is built so they can adopt it
later. Rationale: keep the replay work focused. *Status: **closed 2026-06-11** — see below.*

### 2026-06-11 — Stinger + ChaseStinger brand-themed (closes the un-migrated loose end)
Both base stingers now wipe in the brand motif so every transition matches the rest of the
package and reads as the big-bold-blocks signature. `Stinger/constants.ts` `DEFAULT_PALETTE`
now imports `BRAND_BARS` (orange→green→lime→purple→magenta); `ChaseStinger`'s default
`panelColors` is `BRAND_BARS` too. **Deliberately NOT rebranded:** the `ChaseStinger` robots
(blue/yellow team colours + ID dots) and the orange ball — those are SSL *team identity*, kept
separate from brand theme per the 2026-06-01 team-colours rule. Verified: full opaque coverage
at both transition points (Stinger frame 45, Chase frame 50 — topmost panel = magenta), brand
colours arrive left→right in motif order, `alpha_mode : 1` intact on both re-renders.
*Status: active.*
