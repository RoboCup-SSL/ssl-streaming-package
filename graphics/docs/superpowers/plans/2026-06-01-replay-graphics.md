# Replay Graphics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a RoboCup 2026-themed **replay stinger** (OBS scene transition) and a seamlessly **looping replay frame overlay**, both driven by a new central `src/theme/` token module, as transparent VP9 WebMs.

**Architecture:** Both graphics are one shared `FrameBorder` (nested coloured rings) whose total thickness is fixed for the overlay and animated for the stinger (grow → cover → settle at the frame thickness → clear). Pure math lives in `src/Replay/frame.ts`; all colours/sizes/timings come from `src/theme/`. Existing `Stinger`/`ChaseStinger` are untouched.

**Tech Stack:** Remotion 4.0.464, React 19, TypeScript, Zod 4 (`@remotion/zod-types`), Vitest.

**Project preferences:**
- **No git operations** — save files to disk only; skip every commit step.
- **Visual-first testing** — only two automated tests (coverage invariant + loop seam); everything else verified by render + ffprobe + browser/OBS composite. See `DESIGN_DECISION_DOCUMENT.md`.

---

## File Structure

```
src/theme/index.ts          # NEW design tokens (palette, motif, frame, timings, assets, easing)
src/Replay/frame.ts         # NEW pure math: bandLayout(), replayThickness(), pulse()
src/Replay/frame.test.ts    # NEW minimal tests: cover-hold coverage + pulse loop-seam
src/Replay/schema.ts        # NEW Zod schemas (stinger + overlay)
src/Replay/FrameBorder.tsx  # NEW nested bordered divs, shared by both compositions
src/Replay/ReplayStinger.tsx# NEW composition: animated thickness + REPLAY hold callout
src/Replay/ReplayOverlay.tsx# NEW composition: fixed thickness + REPLAY badge + pulsing dot
src/Root.tsx                # MODIFY: register ReplayStinger + ReplayOverlay
package.json                # MODIFY: 4 render scripts
public/                     # NEW: copy mascot + logo for Remotion staticFile (future use)
README.md                   # MODIFY: replay section + OBS wiring
```

---

## Task 1: Central theme module

**Files:**
- Create: `src/theme/index.ts`

- [ ] **Step 1: Implement** `src/theme/index.ts`:

```ts
import {easeInOut} from '../Stinger/wipe';

export const CANVAS = {width: 3840, height: 2160};
export const FPS = 60;

// RoboCup 2026 brand palette — sampled from 2026.robocup.org (see DESIGN_DECISION_DOCUMENT.md).
export const BRAND = {
  orange: '#F26223',
  green: '#55B748',
  lime: '#CDDC29',
  purple: '#804FA0',
  magenta: '#E63D66',
  paper: '#F5F6FE',
  ink: '#1a1a1e',
};

// The signature ordered 5-colour motif (outer -> inner for frames).
export const BRAND_BARS: string[] = [
  BRAND.orange,
  BRAND.green,
  BRAND.lime,
  BRAND.purple,
  BRAND.magenta,
];

// The thin 5-colour frame: total px thickness (split evenly across the bands).
export const FRAME = {
  thickness: 120,
  bands: BRAND_BARS,
};

// Timings in frames @ FPS.
export const TIMING = {
  stingerDuration: 90, // 1.5s
  holdFrames: 10, // covered hold for the OBS scene swap
  settleFrames: 12, // beat where the stinger frame equals the overlay
  loopDuration: 120, // overlay loop length (2s)
  pulsePeriod: 120, // divides loopDuration -> seamless loop
};

// Static assets, served by Remotion from public/ (wired for future graphics).
export const ASSETS = {
  mascot: 'mascot_with_ball.png',
  logo: 'logo_w.png',
};

export const EASING = easeInOut;
```

- [ ] **Step 2: Type-check** — `npx tsc --noEmit`. Expected: no errors.

---

## Task 2: Pure math + minimal tests

**Files:**
- Create: `src/Replay/frame.ts`
- Test: `src/Replay/frame.test.ts`

- [ ] **Step 1: Implement** `src/Replay/frame.ts`:

```ts
import {interp} from '../Stinger/wipe';

export interface Band {
  inset: number;
  thickness: number;
}

// Split a total border thickness into n equal concentric bands.
export const bandLayout = (totalThickness: number, n: number): Band[] => {
  const t = totalThickness / n;
  return Array.from({length: n}, (_, i) => ({inset: i * t, thickness: t}));
};

export interface ReplayThicknessArgs {
  frame: number;
  duration: number;
  holdFrames: number;
  settleFrames: number;
  coverThickness: number; // thickness that fully covers the screen (>= width/2)
  frameThickness: number; // the thin resting frame thickness (== overlay)
}

// Total border thickness across the stinger's five phases:
//   grow -> cover hold -> settle-in -> settle hold -> reveal.
// During the cover hold thickness == coverThickness (screen solid -> OBS swap).
// During the settle hold thickness == frameThickness (identical to the overlay).
// Thickness is 0 at frame 0 and at the last frame (fully revealed).
export const replayThickness = ({
  frame,
  duration,
  holdFrames,
  settleFrames,
  coverThickness,
  frameThickness,
}: ReplayThicknessArgs): number => {
  const last = duration - 1;
  const coverEnd = Math.round((duration - holdFrames) / 2); // grow ends
  const holdEnd = coverEnd + holdFrames; // cover hold ends (OBS swap window)
  const remaining = last - holdEnd;
  const settleIn = Math.max(1, Math.round((remaining - settleFrames) / 2));
  const settleHoldEnd = holdEnd + settleIn + settleFrames;

  if (frame <= coverEnd) {
    return interp(frame, [0, coverEnd], [0, coverThickness]);
  }
  if (frame <= holdEnd) {
    return coverThickness;
  }
  if (frame <= holdEnd + settleIn) {
    return interp(frame, [holdEnd, holdEnd + settleIn], [coverThickness, frameThickness]);
  }
  if (frame <= settleHoldEnd) {
    return frameThickness;
  }
  return interp(frame, [settleHoldEnd, last], [frameThickness, 0]);
};

// Seamless 0..1 pulse for the REPLAY dot. `period` should divide the loop length.
export const pulse = ({frame, period}: {frame: number; period: number}): number =>
  0.5 + 0.5 * Math.sin((2 * Math.PI * frame) / period);
```

- [ ] **Step 2: Write the two invariant tests** — `src/Replay/frame.test.ts`:

```ts
import {describe, it, expect} from 'vitest';
import {replayThickness, pulse} from './frame';
import {CANVAS} from '../theme';

describe('replayThickness — OBS coverage invariant', () => {
  it('stays >= width/2 across the whole cover-hold window', () => {
    const duration = 90;
    const holdFrames = 10;
    const coverThickness = Math.ceil(CANVAS.width / 2); // 1920
    const coverEnd = Math.round((duration - holdFrames) / 2); // 40
    const holdEnd = coverEnd + holdFrames; // 50
    for (let f = coverEnd; f <= holdEnd; f++) {
      const t = replayThickness({
        frame: f,
        duration,
        holdFrames,
        settleFrames: 12,
        coverThickness,
        frameThickness: 120,
      });
      expect(t).toBeGreaterThanOrEqual(CANVAS.width / 2);
    }
  });
});

describe('pulse — seamless loop', () => {
  it('returns the same value at frame 0 and at one full period', () => {
    expect(pulse({frame: 0, period: 120})).toBeCloseTo(pulse({frame: 120, period: 120}));
  });
});
```

- [ ] **Step 3: Run the tests** — `npx vitest run src/Replay/frame.test.ts`. Expected: 2 passing. (Existing 12 tests remain unaffected.)

---

## Task 3: Schema + FrameBorder component

**Files:**
- Create: `src/Replay/schema.ts`
- Create: `src/Replay/FrameBorder.tsx`

- [ ] **Step 1: Implement** `src/Replay/schema.ts`:

```ts
import {z} from 'zod';
import {zColor} from '@remotion/zod-types';

export const replayStingerSchema = z.object({
  bands: z.array(zColor()).min(1),
  holdFrames: z.number().int().min(0).max(40),
  settleFrames: z.number().int().min(0).max(40),
  frameThickness: z.number().int().min(2).max(400),
  label: z.string(),
});

export const replayOverlaySchema = z.object({
  bands: z.array(zColor()).min(1),
  frameThickness: z.number().int().min(2).max(400),
  label: z.string(),
});
```

- [ ] **Step 2: Implement** `src/Replay/FrameBorder.tsx`:

```tsx
import React from 'react';
import {bandLayout} from './frame';

// A hollow rectangular frame rendered as `bands.length` concentric coloured rings.
// Each ring is an absolutely-positioned div, inset on all sides and given a
// one-band-thick border (box-sizing: border-box so the border draws inward). When
// `thickness` >= width/2 the rings overlap into a solid fill (the stinger's cover
// phase); when thin they read as a crisp multi-colour frame (the overlay).
export const FrameBorder: React.FC<{thickness: number; bands: string[]}> = ({
  thickness,
  bands,
}) => {
  if (thickness <= 0) {
    return null;
  }
  const layout = bandLayout(thickness, bands.length);
  return (
    <>
      {bands.map((color, i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            top: layout[i].inset,
            left: layout[i].inset,
            right: layout[i].inset,
            bottom: layout[i].inset,
            border: `${layout[i].thickness}px solid ${color}`,
            boxSizing: 'border-box',
          }}
        />
      ))}
    </>
  );
};
```

- [ ] **Step 3: Type-check** — `npx tsc --noEmit`. Expected: no errors.

---

## Task 4: ReplayStinger composition

**Files:**
- Create: `src/Replay/ReplayStinger.tsx`

- [ ] **Step 1: Implement** `src/Replay/ReplayStinger.tsx`:

```tsx
import React from 'react';
import {z} from 'zod';
import {AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate} from 'remotion';
import {replayStingerSchema} from './schema';
import {FrameBorder} from './FrameBorder';
import {replayThickness} from './frame';

const LABEL_FADE_FRAMES = 4;

export const ReplayStinger: React.FC<z.infer<typeof replayStingerSchema>> = ({
  bands,
  holdFrames,
  settleFrames,
  frameThickness,
  label,
}) => {
  const frame = useCurrentFrame();
  const {width, durationInFrames} = useVideoConfig();
  const coverThickness = Math.ceil(width / 2); // fully covers the canvas

  const thickness = replayThickness({
    frame,
    duration: durationInFrames,
    holdFrames,
    settleFrames,
    coverThickness,
    frameThickness,
  });

  // 'REPLAY' is visible only during the covered hold (same pattern as Stinger.tsx;
  // short-circuit holdFrames=0 to avoid duplicate interpolate keyframes).
  const coverEnd = Math.round((durationInFrames - holdFrames) / 2);
  const holdEnd = coverEnd + holdFrames;
  const labelOpacity =
    holdFrames <= 0
      ? 0
      : interpolate(
          frame,
          [coverEnd - LABEL_FADE_FRAMES, coverEnd, holdEnd, holdEnd + LABEL_FADE_FRAMES],
          [0, 1, 1, 0],
          {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
        );

  return (
    <AbsoluteFill>
      <FrameBorder thickness={thickness} bands={bands} />
      {label ? (
        <AbsoluteFill
          style={{justifyContent: 'center', alignItems: 'center', opacity: labelOpacity}}
        >
          <h1
            style={{
              color: 'white',
              fontFamily: 'sans-serif',
              fontSize: 320,
              fontWeight: 800,
              letterSpacing: 8,
              margin: 0,
            }}
          >
            {label}
          </h1>
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: Type-check** — `npx tsc --noEmit`. Expected: no errors.

---

## Task 5: ReplayOverlay composition

**Files:**
- Create: `src/Replay/ReplayOverlay.tsx`

- [ ] **Step 1: Implement** `src/Replay/ReplayOverlay.tsx`:

```tsx
import React from 'react';
import {z} from 'zod';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {replayOverlaySchema} from './schema';
import {FrameBorder} from './FrameBorder';
import {pulse} from './frame';
import {BRAND, TIMING} from '../theme';

export const ReplayOverlay: React.FC<z.infer<typeof replayOverlaySchema>> = ({
  bands,
  frameThickness,
  label,
}) => {
  const frame = useCurrentFrame();
  const p = pulse({frame, period: TIMING.pulsePeriod});
  const dotOpacity = 0.35 + 0.65 * p;
  const dotScale = 0.85 + 0.3 * p;

  return (
    <AbsoluteFill>
      <FrameBorder thickness={frameThickness} bands={bands} />
      {/* REPLAY badge centred on the top border. */}
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'flex-start'}}>
        <div
          style={{
            marginTop: Math.max(0, frameThickness - 8),
            display: 'flex',
            alignItems: 'center',
            gap: 24,
            background: BRAND.ink,
            color: '#ffffff',
            padding: '18px 44px',
            borderRadius: 999,
            fontFamily: 'sans-serif',
            fontSize: 64,
            fontWeight: 800,
            letterSpacing: 6,
            boxShadow: '0 8px 30px rgba(0,0,0,0.35)',
          }}
        >
          <span
            style={{
              width: 36,
              height: 36,
              borderRadius: '50%',
              background: BRAND.magenta,
              opacity: dotOpacity,
              transform: `scale(${dotScale})`,
            }}
          />
          {label}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: Type-check** — `npx tsc --noEmit`. Expected: no errors.

---

## Task 6: Register compositions + scripts + assets

**Files:**
- Modify: `src/Root.tsx`
- Modify: `package.json`
- Create: `public/` (copy assets)

- [ ] **Step 1: Add imports to `src/Root.tsx`** (after the existing ChaseStinger imports):

```tsx
import {ReplayStinger} from './Replay/ReplayStinger';
import {ReplayOverlay} from './Replay/ReplayOverlay';
import {replayStingerSchema, replayOverlaySchema} from './Replay/schema';
import {FRAME, TIMING, BRAND_BARS} from './theme';
```

- [ ] **Step 2: Add two `<Composition>` blocks to `src/Root.tsx`** inside the fragment, after the ChaseStinger composition:

```tsx
      <Composition
        id="ReplayStinger"
        component={ReplayStinger}
        durationInFrames={TIMING.stingerDuration}
        fps={FPS}
        width={DIMENSIONS.width}
        height={DIMENSIONS.height}
        schema={replayStingerSchema}
        defaultProps={{
          bands: BRAND_BARS,
          holdFrames: TIMING.holdFrames,
          settleFrames: TIMING.settleFrames,
          frameThickness: FRAME.thickness,
          label: 'REPLAY',
        }}
      />
      <Composition
        id="ReplayOverlay"
        component={ReplayOverlay}
        durationInFrames={TIMING.loopDuration}
        fps={FPS}
        width={DIMENSIONS.width}
        height={DIMENSIONS.height}
        schema={replayOverlaySchema}
        defaultProps={{
          bands: BRAND_BARS,
          frameThickness: FRAME.thickness,
          label: 'REPLAY',
        }}
      />
```

(`FPS`, `DIMENSIONS` are already imported in Root.tsx from `./Stinger/constants`.)

- [ ] **Step 3: Add render scripts to `package.json`** `"scripts"` block:

```json
    "render:replay-stinger": "remotion render ReplayStinger out/replay-stinger.webm --codec=vp9 --image-format=png",
    "render:replay-stinger:preview": "remotion render ReplayStinger out/replay-stinger-preview.webm --codec=vp9 --image-format=png --scale=0.25",
    "render:replay-overlay": "remotion render ReplayOverlay out/replay-overlay.webm --codec=vp9 --image-format=png",
    "render:replay-overlay:preview": "remotion render ReplayOverlay out/replay-overlay-preview.webm --codec=vp9 --image-format=png --scale=0.25"
```

- [ ] **Step 4: Copy assets into `public/`**:

```bash
mkdir -p public
cp assets/mascot_with_ball.png public/mascot_with_ball.png
cp out/brand/logo_w.png public/logo_w.png
```

- [ ] **Step 5: Verify both compositions register** — `npx remotion compositions`. Expected: lists `Stinger`, `ChaseStinger`, `ReplayStinger` (90 frames), `ReplayOverlay` (120 frames), all 3840×2160 @ 60fps.

- [ ] **Step 6: Type-check + tests** — `npx tsc --noEmit` (no errors) and `npm run test` (existing 12 + new 2 pass).

---

## Task 7: Render, verify alpha + readability, README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Render fast previews**:

```bash
npm run render:replay-stinger:preview
npm run render:replay-overlay:preview
```

Expected: `out/replay-stinger-preview.webm` (960×540, 90 frames) and `out/replay-overlay-preview.webm` (960×540, 120 frames), no errors.

- [ ] **Step 2: Verify alpha** — for each file:

```bash
npx remotion ffprobe out/replay-stinger-preview.webm | grep alpha_mode
npx remotion ffprobe out/replay-overlay-preview.webm | grep alpha_mode
```

Expected: `alpha_mode : 1` for both.

- [ ] **Step 3: Visual check via stills** — export key frames over a magenta backdrop in a browser, or extract stills:

```bash
npx remotion still ReplayStinger out/rs-grow.png   --frame=20 --scale=0.25
npx remotion still ReplayStinger out/rs-cover.png  --frame=45 --scale=0.25
npx remotion still ReplayStinger out/rs-settle.png --frame=64 --scale=0.25
npx remotion still ReplayStinger out/rs-reveal.png --frame=80 --scale=0.25
npx remotion still ReplayOverlay out/ro-a.png --frame=0  --scale=0.25
npx remotion still ReplayOverlay out/ro-b.png --frame=60 --scale=0.25
```

Confirm: cover frame is fully opaque (no transparency in the centre); settle frame shows the thin 5-colour frame; overlay shows frame + REPLAY badge.

- [ ] **Step 4: Append a README section**:

````markdown

## Replay graphics

Two RoboCup 2026-themed pieces for replays, both driven by `src/theme/`:

- **ReplayStinger** — an OBS scene transition (use it as the *Stinger* transition
  between your Live and Replay scenes; it serves both directions, transition point
  ≈ frame 43 / ~720 ms). The 5 brand-colour bars sweep in to full coverage, then
  settle into a thin frame before clearing.
- **ReplayOverlay** — a seamlessly **looping** frame overlay with a "REPLAY" badge
  and pulsing dot. Add `replay-overlay.webm` as a looping media source on the Replay
  scene, above the footage.

```bash
npm run render:replay-stinger    # full 4K -> out/replay-stinger.webm
npm run render:replay-overlay    # full 4K -> out/replay-overlay.webm (loop this in OBS)
npm run render:replay-stinger:preview
npm run render:replay-overlay:preview
```

Colours, frame thickness, and timings are tokens in `src/theme/index.ts` — tune
once and re-render to re-theme every graphic. Decision history:
`DESIGN_DECISION_DOCUMENT.md`.
````

- [ ] **Step 5: Clean up scratch** — remove temp stills: `rm -f out/rs-*.png out/ro-*.png`.

---

## Done

`ReplayStinger` and `ReplayOverlay` render alongside the existing stingers: a
transparent VP9 replay transition that resolves into the same 5-colour frame the
looping overlay wears, all themed from `src/theme/`. Coverage + loop-seam guarded by
two tests; everything else verified visually.
