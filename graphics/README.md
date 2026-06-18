# OBS Stinger Template (Remotion)

A reusable, parameterized stinger transition. Produces a transparent (true-alpha)
VP9 WebM for use as an OBS Stinger scene transition.

## Customize

```bash
npm run dev
```

Opens Remotion Studio. Use the sidebar controls to change:

- **direction** — which way the panels travel (`left` / `right` / `up` / `down`)
- **panelColors** — one full-screen colored layer per color (last color is on top)
- **stagger** — frames of delay between panels
- **holdFrames** — how long the screen stays fully covered (the OBS swap window)
- **title** — optional centered wordmark shown while the screen is covered

## Render

```bash
npm run render          # 1080p -> out/stinger.webm
npm run render:preview  # fast 960x540 sanity check -> out/stinger-preview.webm
```

> Compositions are authored at 3840×2160; the `render:*` scripts output **1920×1080**
> via `--codec=vp9 --image-format=png --scale=0.5`. Drop `--scale=0.5` (or set `--scale=1`)
> for native 4K; `:preview` scripts use `--scale=0.25` (960×540).

The output is a VP9 WebM with a real alpha channel. Verify it carries alpha:

```bash
npx remotion ffprobe out/stinger.webm | grep alpha_mode   # expect: alpha_mode : 1
```

> **Why not `yuva420p`?** VP9 stores its alpha plane in a per-frame
> `BlockAdditional` element, flagged by the stream-level `alpha_mode : 1` tag —
> *not* in the pixel-format name. `ffprobe` reports the primary plane as
> `yuv420p`; that is expected and does **not** mean transparency was lost. The
> ffmpeg **command-line** decoder also ignores that alpha plane, so extracting a
> still with `ffmpeg` shows transparent areas as black. Real consumers —
> **OBS** and Chromium-based browsers — decode the alpha correctly. To eyeball it,
> drop the file onto a brightly colored OBS scene and confirm the background shows
> through the transparent regions.

## Use in OBS

1. **Settings → Scene Transitions** (or the Scene Transitions panel) → **+** → **Stinger**.
2. **Video File** → select `out/stinger.webm`.
3. **Transition Point** → set to **750 ms** (the middle of the hold window, where
   OBS swaps scenes behind the fully-covered screen).
4. Click **OK**, then use the transition when switching scenes.

> The video is 1.5 s at 60 fps. The screen is fully opaque from ~0.67 s to ~0.83 s;
> the 750 ms transition point sits in the middle of that window so the scene swap
> is always hidden.

## ChaseStinger variant

`ChaseStinger` is the same panel wipe with a top-down RoboCup scene on top: an
orange ball and six robots (3 blue + 3 yellow, distinct IDs) streak left→right at
constant speed. Two "scout" robots drive in first — before the purple wipe appears —
then the wipe sweeps in with the ball and the chasing pack, which crosses centre
during the covered hold.

```bash
npm run render:chase           # 1080p -> out/chase-stinger.webm
npm run render:chase:preview   # fast 960x540 sanity check
```

Extra Studio knobs (on top of the wipe controls):

- `robots` — each with a team centre-dot colour + four ID-dot colours; array length
  is how many are in the pack.
- `scouts` — how many lead robots drive in ahead of the ball (clamped to the roster size).
- `trail` — frames each successive actor lags the one ahead.
- `wipeDelay` — frames the purple wipe is held back so the scouts get a pre-roll on
  the transparent screen.

Use it in OBS like the base stinger, but set the **transition point to ~830 ms** —
delaying the wipe shifts the covered moment later than the base stinger's 750 ms.

## Replay graphics

Two RoboCup 2026-themed pieces for replays, both driven by the central theme module
`src/theme/index.ts` (palette, frame thickness, timings). Tune a token there and
re-render to re-theme every graphic.

- **ReplayOverlay** — a seamlessly **looping** frame overlay (a "REPLAY" badge with a
  pulsing dot on the 5-colour frame). Add `replay-overlay.webm` as a media source on
  the Replay scene **set to loop**, layered above the replay footage. Its only motion
  is the pulse, timed so the loop has no visible seam.

### Directional replay transitions (recommended)

Robot-chase stingers (the `ChaseStinger` machinery, brand-recoloured) that read as a
rewind/resume — this is the recommended way to enter/leave replay:

- **ReplayRewindStinger** (live → replay) — robots roll **right→left while facing
  right** under a **VHS tape-shuttle overlay** (scanlines, a rolling tracking bar,
  tape-jitter, and a blinking ◄◄ REWIND glyph) so it reads unmistakably as a rewind.
  Wire it as the Stinger transition Live → Replay. (FX tunable via `theme.REWIND`.)
- **ReplayResumeStinger** (replay → live) — robots drive **forward left→right**: a
  "resume". Wire it Replay → Live.

(OBS lets you set a different Stinger transition per scene-change direction.)

```bash
npm run render:replay-overlay          # 1080p -> out/replay-overlay.webm (loop this in OBS)
npm run render:replay-rewind           # 1080p -> out/replay-rewind.webm  (Live -> Replay)
npm run render:replay-resume           # 1080p -> out/replay-resume.webm  (Replay -> Live)
# each has a matching :preview script at 960x540
```

## Standby / between-match graphics (modular)

A family of **opaque, native-1080p** holding graphics for between matches, split into
**reusable pieces you stack in OBS** so the same elements serve both the no-host holding
screen *and* a webcam scene:

- **`BreathingBackground`** — thick **brand-colour bars** lined up left→right and **tilted
  ~15°** (hard edges, no fades) with a **breathing wave** that swells each colour in turn
  (left→right→left). On its own: a reusable looping backdrop. → `out/breathing-background.mp4`.
- **`NextMatch`** — just the baked **"NEXT MATCH IN"** label + a reserved slot for the live
  countdown number, on a solid panel, on a **transparent** compact canvas. Drop it over any
  background/webcam in OBS and scale/position it freely. → `out/next-match.png`.
- **`Standby`** — the thin **combo**: `BreathingBackground` + the next-match block + the DAON
  mascot + logo, full-screen. The one-file between-match holding screen. → `out/standby.mp4`.

`BreathingBackground` and `Standby` are **opaque** (root fills with the `paper` base) and
authored **natively at 1920×1080** — no `--scale`. Being opaque they encode as **H.264 MP4**
(far faster than VP9 — see *Render speed*). `NextMatch` has no motion, so it's a single
**transparent PNG** (the transparency invariant applies to it).

```bash
npm run render:bg               # 1920x1080 -> out/breathing-background.mp4 (loop in OBS)
npm run render:next-match       #            -> out/next-match.png (transparent block)
npm run render:standby          # 1920x1080 -> out/standby.mp4 (combined holding screen)
npm run render:bg:preview       # fast 960x540 sanity check
npm run render:standby:preview  # fast 960x540 sanity check
```

The countdown **number is not baked in** — a pre-rendered file can't know the real seconds
remaining. Supply it live in OBS over the reserved slot.

**Holding scene (no host):** add `out/standby.mp4` as a **Media Source** and **set it to
loop** (right-click → Properties → *Loop*; the background repeats seamlessly, loop length set
in `theme.STANDBY`). Add a **Text (GDI+)** source above it for the number, over the dashed
slot (just left-of-centre, on the orange baseline) — edit by hand or drive it with a countdown
plugin (e.g. Snaz).

**Webcam scene (host talking):** add `out/breathing-background.mp4` (looped) as the full-screen
backdrop → your webcam source on top, sized a bit smaller so the bars breathe around its edges
(the bars *become* the border — no separate frame graphic needed) → `out/next-match.png` scaled
into a corner → a Text source for the number over its slot.

Re-render with the `label` prop changed (`"BACK SOON"`, `"KICKOFF IN"`, …) for variants. Turn
`showSlotGuide` off in Studio for a clean final render once the OBS text is aligned.

Studio knobs: `BreathingBackground` → `bands`, `loopDuration`; `NextMatch` → `label`,
`sublabel`, `showSlotGuide`; `Standby` → all of the above. Design rationale:
`docs/superpowers/specs/2026-06-10-standby-design.md` (original) and
`docs/superpowers/specs/2026-06-11-modular-standby-design.md` (the modular split).

## Render speed

`remotion.config.ts` turns on two speedups for **every** render (and Studio):

- **GPU rendering** — `Config.setChromiumOpenGlRenderer('angle')` uses the GPU for the
  Chromium/rasterization stage.
- **Concurrency** — `Config.setConcurrency(cores − 2)` renders that many frames in parallel.

This accelerates the *rendering* stage. **Encoding is separate:** the transparent
stingers/overlays must use **VP9**, whose alpha encoder is **CPU-only** — no GPU encoder
(NVENC/QSV/VAAPI) supports alpha video, and Remotion's hardware acceleration is macOS-only
anyway. They're short (90 frames), so this is fine. The **opaque `Standby`** avoids VP9
entirely by encoding **H.264**, which dropped its render from ~4:43 to ~1:20.

Quick wins if a render still drags: lower `--scale`, or (for opaque output) prefer H.264.

Cross-cutting design decisions (brand tokens, the rewind/resume pair, the visual-first
testing call) live in `DESIGN_DECISION_DOCUMENT.md`.
