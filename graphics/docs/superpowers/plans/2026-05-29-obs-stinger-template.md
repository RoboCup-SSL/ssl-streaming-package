# OBS Stinger Template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Remotion project with one parameterized `Stinger` composition that renders a transparent (true-alpha) VP9 WebM panel-wipe transition for use as an OBS Stinger.

**Architecture:** A pure, dependency-free math module (`wipe.ts`) computes each panel's position as a function of the current frame; React components (`Panels`, `Stinger`) consume that math and render colored full-screen layers over a transparent root. A Zod schema exposes the knobs (direction, colors, stagger, hold, title) as live controls in Remotion Studio. The pure math is unit-tested with Vitest; the visual output is verified observationally in Studio and via `ffprobe` on the rendered file.

**Tech Stack:** Remotion 4.x, React, TypeScript, Zod (`@remotion/zod-types` for color pickers), Vitest.

**Note on testing philosophy:** The animation *math* is a pure function and gets real TDD (Task 3). React components that produce pixels are not meaningfully unit-testable here — they are verified by observation in Studio (transparency checkerboard, full coverage during hold) and by inspecting the rendered file's pixel format. Those verification steps are explicit and required.

---

## File Structure

```
remotion/
  .gitignore                 # node_modules, out/
  package.json               # deps + scripts (dev, render, test)
  tsconfig.json              # TS config
  remotion.config.ts         # png image format + vp9 + yuva420p alpha defaults
  README.md                  # OBS setup instructions (Task 6)
  src/
    index.ts                 # registerRoot entry point
    Root.tsx                 # registers <Composition id="Stinger">
    Stinger/
      constants.ts           # dimensions, fps, duration, default palette
      schema.ts              # zod props schema (+ .test.ts)
      wipe.ts                # pure animation math (+ .test.ts)
      Panels.tsx             # the wipe engine (renders colored layers)
      Stinger.tsx            # composition root: panels + optional title
```

---

## Task 1: Project scaffold, dependencies, and config

**Files:**
- Create: `package.json`, `tsconfig.json`, `remotion.config.ts`, `.gitignore`

- [ ] **Step 1: Verify Node version**

Run: `node -v`
Expected: `v18.x` or higher (Remotion requires Node 18+). If lower, stop and upgrade Node.

- [ ] **Step 2: Initialize package.json**

Run: `npm init -y`
Expected: creates `package.json`.

- [ ] **Step 3: Install Remotion + React + tooling**

Install all Remotion packages in one command so they resolve to the same version (Remotion requires every `@remotion/*` package and `remotion` to share an identical version):

```bash
npm i remotion@latest @remotion/cli@latest @remotion/zod-types@latest react react-dom zod
npm i -D typescript @types/react @types/react-dom vitest
```
Expected: installs without peer-dependency errors.

- [ ] **Step 4: Write `package.json` scripts**

Open `package.json` and set the `"scripts"` block (leave the auto-generated `dependencies`/`devDependencies` untouched):

```json
{
  "scripts": {
    "dev": "remotion studio",
    "render": "remotion render Stinger out/stinger.webm --codec=vp9 --image-format=png",
    "render:preview": "remotion render Stinger out/stinger-preview.webm --codec=vp9 --image-format=png --scale=0.25",
    "test": "vitest run"
  }
}
```

- [ ] **Step 5: Write `tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "jsx": "react-jsx",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "noEmit": true
  },
  "include": ["src", "remotion.config.ts"]
}
```

- [ ] **Step 6: Write `remotion.config.ts`**

```ts
import {Config} from '@remotion/cli/config';

// PNG image format is required to carry an alpha channel through the
// frame pipeline. VP9 + no opaque background + yuva420p = real transparency.
Config.setVideoImageFormat('png');
Config.setCodec('vp9');
Config.setPixelFormat('yuva420p');
```

- [ ] **Step 7: Write `.gitignore`**

```
node_modules/
out/
.DS_Store
```

- [ ] **Step 8: Verify the Remotion CLI is available**

Run: `npx remotion --version`
Expected: prints a 4.x version number (no error).

- [ ] **Step 9: Commit**

```bash
git add package.json package-lock.json tsconfig.json remotion.config.ts .gitignore
git commit -m "chore: scaffold Remotion project with vp9 alpha render config"
```

---

## Task 2: Constants and Zod schema

**Files:**
- Create: `src/Stinger/constants.ts`
- Create: `src/Stinger/schema.ts`
- Test: `src/Stinger/schema.test.ts`

- [ ] **Step 1: Write the failing schema test**

`src/Stinger/schema.test.ts`:

```ts
import {describe, it, expect} from 'vitest';
import {stingerSchema} from './schema';

describe('stingerSchema', () => {
  it('parses well-formed props', () => {
    const parsed = stingerSchema.parse({
      direction: 'right',
      panelColors: ['#0e0e12', '#7c3aed'],
      stagger: 4,
      holdFrames: 10,
      title: '',
    });
    expect(parsed.panelColors).toHaveLength(2);
    expect(parsed.direction).toBe('right');
  });

  it('rejects an invalid direction', () => {
    expect(() =>
      stingerSchema.parse({
        direction: 'sideways',
        panelColors: ['#000000'],
        stagger: 4,
        holdFrames: 10,
        title: '',
      }),
    ).toThrow();
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npm run test`
Expected: FAIL — cannot resolve `./schema` (module does not exist yet).

- [ ] **Step 3: Write `src/Stinger/constants.ts`**

```ts
export const DIMENSIONS = {width: 3840, height: 2160};
export const FPS = 60;
export const DURATION = 90; // 1.5 seconds at 60fps

// Tasteful default palette: dark base + two accent purples.
// The LAST color is the topmost layer and the one that dominates during the hold.
export const DEFAULT_PALETTE = ['#0e0e12', '#5b21b6', '#7c3aed'];
```

- [ ] **Step 4: Write `src/Stinger/schema.ts`**

```ts
import {z} from 'zod';
import {zColor} from '@remotion/zod-types';

// zColor() renders as a color picker in the Remotion Studio sidebar.
export const stingerSchema = z.object({
  direction: z.enum(['left', 'right', 'up', 'down']),
  panelColors: z.array(zColor()),
  stagger: z.number().min(0).max(30),
  holdFrames: z.number().min(0).max(40),
  title: z.string(),
});
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `npm run test`
Expected: PASS — both schema tests green.

- [ ] **Step 6: Commit**

```bash
git add src/Stinger/constants.ts src/Stinger/schema.ts src/Stinger/schema.test.ts
git commit -m "feat: add stinger constants and zod props schema"
```

---

## Task 3: Pure wipe animation math (TDD)

**Files:**
- Create: `src/Stinger/wipe.ts`
- Test: `src/Stinger/wipe.test.ts`

This is the core engine. It has **no Remotion or React imports** so it is fast and hermetic to test.

- [ ] **Step 1: Write the failing tests**

`src/Stinger/wipe.test.ts`:

```ts
import {describe, it, expect} from 'vitest';
import {panelOffset, offsetToTransform} from './wipe';

const base = {durationInFrames: 90, holdFrames: 10, stagger: 4};
// With duration 90 and hold 10: coverEnd = 40, revealStart = 50.

describe('panelOffset', () => {
  it('panel 0 starts fully off the leading edge at frame 0', () => {
    expect(panelOffset({...base, panelIndex: 0, frame: 0})).toBe(-100);
  });

  it('panel 0 fully covers (offset 0) at the end of the cover phase', () => {
    expect(panelOffset({...base, panelIndex: 0, frame: 40})).toBeCloseTo(0);
  });

  it('every panel covers (offset 0) throughout the hold window', () => {
    for (const panelIndex of [0, 1, 2]) {
      for (const frame of [41, 45, 49]) {
        expect(panelOffset({...base, panelIndex, frame})).toBe(0);
      }
    }
  });

  it('panel 0 is fully off the trailing edge at the last frame', () => {
    expect(panelOffset({...base, panelIndex: 0, frame: 90})).toBeCloseTo(100);
  });

  it('a staggered panel enters later than panel 0', () => {
    // Panel 1 has entrance delay = 1 * 4 = 4 frames; before that it stays off-screen.
    expect(panelOffset({...base, panelIndex: 1, frame: 2})).toBe(-100);
  });

  it('handles an oversized stagger without producing NaN and still covers during hold', () => {
    const value = panelOffset({
      durationInFrames: 90,
      holdFrames: 10,
      stagger: 1000,
      panelIndex: 3,
      frame: 45,
    });
    expect(Number.isNaN(value)).toBe(false);
    expect(value).toBe(0);
  });
});

describe('offsetToTransform', () => {
  it('maps directions to the correct axis and sign', () => {
    expect(offsetToTransform(-100, 'right')).toBe('translateX(-100%)');
    expect(offsetToTransform(-100, 'left')).toBe('translateX(100%)');
    expect(offsetToTransform(-100, 'down')).toBe('translateY(-100%)');
    expect(offsetToTransform(-100, 'up')).toBe('translateY(100%)');
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `npm run test`
Expected: FAIL — cannot resolve `./wipe`.

- [ ] **Step 3: Write `src/Stinger/wipe.ts`**

```ts
export type Direction = 'left' | 'right' | 'up' | 'down';

export const clamp = (value: number, min: number, max: number): number =>
  Math.min(Math.max(value, min), max);

export const lerp = (a: number, b: number, t: number): number => a + (b - a) * t;

// Cubic ease-in-out; t expected in [0, 1].
export const easeInOut = (t: number): number =>
  t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;

// Map `value` from an input range to an output range, clamped and eased.
export const interp = (
  value: number,
  [inMin, inMax]: [number, number],
  [outMin, outMax]: [number, number],
): number => {
  if (inMax <= inMin) {
    return value >= inMax ? outMax : outMin;
  }
  const t = clamp((value - inMin) / (inMax - inMin), 0, 1);
  return lerp(outMin, outMax, easeInOut(t));
};

export interface PanelOffsetArgs {
  frame: number;
  durationInFrames: number;
  holdFrames: number;
  panelIndex: number;
  stagger: number;
}

// Position of a panel along its travel axis, as a percentage:
//   -100 = fully off the leading edge (not yet covering)
//      0 = covering the screen
//   +100 = fully off the trailing edge (revealed)
//
// Timeline (e.g. duration 90, hold 10):
//   cover   frames 0..coverEnd      panels slide -100 -> 0
//   hold    frames coverEnd..revealStart   all panels held at 0 (screen covered)
//   reveal  frames revealStart..duration    panels slide 0 -> 100
//
// Each panel is delayed by `panelIndex * stagger`. Entrance delays are clamped so
// every panel still reaches 0 by coverEnd, guaranteeing full coverage during hold.
export const panelOffset = ({
  frame,
  durationInFrames,
  holdFrames,
  panelIndex,
  stagger,
}: PanelOffsetArgs): number => {
  const coverEnd = (durationInFrames - holdFrames) / 2;
  const revealStart = coverEnd + holdFrames;
  const entrance = Math.min(panelIndex * stagger, coverEnd - 1);
  const exitStart = Math.min(
    revealStart + panelIndex * stagger,
    durationInFrames - 1,
  );

  if (frame <= coverEnd) {
    return interp(frame, [entrance, coverEnd], [-100, 0]);
  }
  if (frame < exitStart) {
    return 0;
  }
  return interp(frame, [exitStart, durationInFrames], [0, 100]);
};

// Convert a travel-axis percentage into a CSS transform for the given direction.
// `direction` is the direction the panels travel toward.
export const offsetToTransform = (
  percent: number,
  direction: Direction,
): string => {
  switch (direction) {
    case 'right':
      return `translateX(${percent}%)`;
    case 'left':
      return `translateX(${-percent}%)`;
    case 'down':
      return `translateY(${percent}%)`;
    case 'up':
      return `translateY(${-percent}%)`;
  }
};
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npm run test`
Expected: PASS — all `wipe` and `schema` tests green.

- [ ] **Step 5: Commit**

```bash
git add src/Stinger/wipe.ts src/Stinger/wipe.test.ts
git commit -m "feat: add pure panel-wipe animation math with tests"
```

---

## Task 4: Panels component (the wipe engine)

**Files:**
- Create: `src/Stinger/Panels.tsx`

Verified observationally in Task 5 once the composition is registered (a component alone cannot be rendered without a `<Composition>`).

- [ ] **Step 1: Write `src/Stinger/Panels.tsx`**

```tsx
import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {Direction, panelOffset, offsetToTransform} from './wipe';

// Renders one full-screen colored layer per color. Layers are stacked in array
// order (last color on top). Each layer sweeps across using the pure wipe math.
export const Panels: React.FC<{
  colors: string[];
  direction: Direction;
  stagger: number;
  holdFrames: number;
}> = ({colors, direction, stagger, holdFrames}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();

  return (
    <>
      {colors.map((color, panelIndex) => {
        const percent = panelOffset({
          frame,
          durationInFrames,
          holdFrames,
          panelIndex,
          stagger,
        });
        return (
          <AbsoluteFill
            key={panelIndex}
            style={{
              backgroundColor: color,
              transform: offsetToTransform(percent, direction),
            }}
          />
        );
      })}
    </>
  );
};
```

- [ ] **Step 2: Commit**

```bash
git add src/Stinger/Panels.tsx
git commit -m "feat: add Panels wipe-engine component"
```

---

## Task 5: Stinger composition + registration + Studio verification

**Files:**
- Create: `src/Stinger/Stinger.tsx`
- Create: `src/Root.tsx`
- Create: `src/index.ts`

- [ ] **Step 1: Write `src/Stinger/Stinger.tsx`**

The root `AbsoluteFill` has **no `backgroundColor`** — it stays transparent. Only the panels carry color. The optional title fades in around the hold window.

```tsx
import React from 'react';
import {z} from 'zod';
import {AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate} from 'remotion';
import {stingerSchema} from './schema';
import {Panels} from './Panels';

export const Stinger: React.FC<z.infer<typeof stingerSchema>> = ({
  direction,
  panelColors,
  stagger,
  holdFrames,
  title,
}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const coverEnd = (durationInFrames - holdFrames) / 2;
  const revealStart = coverEnd + holdFrames;

  // Title is visible only while the screen is covered (the hold window).
  const titleOpacity = interpolate(
    frame,
    [coverEnd - 4, coverEnd, revealStart, revealStart + 4],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  return (
    <AbsoluteFill>
      <Panels
        colors={panelColors}
        direction={direction}
        stagger={stagger}
        holdFrames={holdFrames}
      />
      {title ? (
        <AbsoluteFill
          style={{justifyContent: 'center', alignItems: 'center', opacity: titleOpacity}}
        >
          <h1
            style={{
              color: 'white',
              fontFamily: 'sans-serif',
              fontSize: 220,
              fontWeight: 800,
              letterSpacing: -4,
              margin: 0,
            }}
          >
            {title}
          </h1>
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: Write `src/Root.tsx`**

```tsx
import React from 'react';
import {Composition} from 'remotion';
import {Stinger} from './Stinger/Stinger';
import {stingerSchema} from './Stinger/schema';
import {DIMENSIONS, FPS, DURATION, DEFAULT_PALETTE} from './Stinger/constants';

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="Stinger"
      component={Stinger}
      durationInFrames={DURATION}
      fps={FPS}
      width={DIMENSIONS.width}
      height={DIMENSIONS.height}
      schema={stingerSchema}
      defaultProps={{
        direction: 'right' as const,
        panelColors: DEFAULT_PALETTE,
        stagger: 4,
        holdFrames: 10,
        title: '',
      }}
    />
  );
};
```

- [ ] **Step 3: Write `src/index.ts`**

```ts
import {registerRoot} from 'remotion';
import {RemotionRoot} from './Root';

registerRoot(RemotionRoot);
```

- [ ] **Step 4: Verify the composition is registered**

Run: `npx remotion compositions`
Expected: output lists a composition with id `Stinger` (3840x2160, 90 frames, 60fps). No type or import errors.

- [ ] **Step 5: Verify the tests still pass**

Run: `npm run test`
Expected: PASS — schema + wipe tests still green.

- [ ] **Step 6: Observational check in Studio (required)**

Run: `npm run dev` (opens Remotion Studio in the browser). Then confirm:
1. The timeline preview shows a **transparency checkerboard** at frame 0 (nothing covering yet).
2. Scrubbing to the middle (~frame 45) shows the screen **fully covered** by the panel color (no checkerboard visible) — this is the OBS swap point.
3. Scrubbing to the end (~frame 89) returns to checkerboard (fully revealed).
4. The Studio sidebar shows editable controls: a direction dropdown, color pickers for `panelColors`, and number fields for `stagger`/`holdFrames`/`title`.

Stop the dev server (Ctrl+C) once confirmed.

- [ ] **Step 7: Commit**

```bash
git add src/Stinger/Stinger.tsx src/Root.tsx src/index.ts
git commit -m "feat: add Stinger composition, registration, and optional title"
```

---

## Task 6: Render, verify alpha, and document OBS setup

**Files:**
- Create: `README.md`

- [ ] **Step 1: Render a fast preview to validate the alpha pipeline**

Run: `npm run render:preview`
Expected: produces `out/stinger-preview.webm` (960x540, fast). No errors.

- [ ] **Step 2: Verify the output carries a real alpha channel**

Run: `npx remotion ffprobe out/stinger-preview.webm`
Expected: the video stream's pixel format is `yuva420p` (the `a` confirms an alpha plane). If it shows `yuv420p` (no alpha), the render lost transparency — re-check that `remotion.config.ts` sets `png` image format and that the root `AbsoluteFill` in `Stinger.tsx` has no `backgroundColor`.

- [ ] **Step 3: Render the full 4K stinger**

Run: `npm run render`
Expected: produces `out/stinger.webm` (3840x2160). This is CPU-heavy and may take several minutes — that is expected for 4K VP9 with alpha.

- [ ] **Step 4: Write `README.md`**

````markdown
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
npm run render          # full 4K -> out/stinger.webm (slow)
npm run render:preview  # fast 960x540 sanity check -> out/stinger-preview.webm
```

The output is VP9 WebM with a `yuva420p` alpha channel. Verify with:

```bash
npx remotion ffprobe out/stinger.webm   # pixel format should be yuva420p
```

## Use in OBS

1. **Settings → Scene Transitions** (or the Scene Transitions panel) → **+** → **Stinger**.
2. **Video File** → select `out/stinger.webm`.
3. **Transition Point** → set to **750 ms** (the middle of the hold window, where
   OBS swaps scenes behind the fully-covered screen).
4. Click **OK**, then use the transition when switching scenes.

> The video is 1.5 s at 60 fps. The screen is fully opaque from ~0.67 s to ~0.83 s;
> the 750 ms transition point sits in the middle of that window so the scene swap
> is always hidden.
````

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: add README with render and OBS setup instructions"
```

---

## Done

After Task 6, you have: a tested wipe engine, a Studio-editable `Stinger` composition, a verified transparent 4K WebM in `out/`, and OBS setup docs. To make variants, open Studio, tweak the knobs, and re-render.
