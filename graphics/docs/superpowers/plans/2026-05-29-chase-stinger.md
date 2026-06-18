# ChaseStinger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new `ChaseStinger` Remotion composition where an orange RoboCup ball streaks left→right with three top-down robots chasing it, layered over the existing panel-wipe stinger (so it still works as a transparent OBS transition).

**Architecture:** New `src/ChaseStinger/` folder reusing the existing `Stinger/Panels.tsx`, `wipe.ts`, and `constants.ts`. A pure, unit-tested `chase.ts` maps frame → actor position; thin React components (`RobotTop`, `Ball`, `ChaseLayer`) render it. The composition root layers the reused `Panels` wipe (transparent root, for OBS coverage) with the chase layer on top. Registered as a second `<Composition>` alongside the untouched `Stinger`.

**Tech Stack:** Remotion 4.0.464, React, TypeScript, Zod (`@remotion/zod-types`), Vitest.

**Testing note:** The chase *math* (`chase.ts`) gets real TDD. The pixel-producing React components are verified observationally (rendered stills + browser composite over magenta), exactly as the base stinger was — not faked into unit tests.

**Project preference:** This project uses **no git operations**. Skip every `git`/commit step in this plan; just save files to disk. (Plan retains task structure otherwise.)

---

## File Structure

```
src/ChaseStinger/
  chase.ts          # pure math: actorX(), laneY()  (+ chase.test.ts)
  constants.ts      # robot/ball sizes, DEFAULT_ROBOTS
  schema.ts         # chaseStingerSchema (reuses stingerSchema), robotSchema  (+ schema.test.ts)
  RobotTop.tsx      # top-down robot from the SSL geometry
  Ball.tsx          # orange SSL ball
  ChaseLayer.tsx    # positions ball + robots via chase.ts
  ChaseStinger.tsx  # composition root: Panels (reused) + ChaseLayer
src/Root.tsx        # MODIFY: register second <Composition id="ChaseStinger">
package.json        # MODIFY: add render:chase / render:chase:preview scripts
```

---

## Task 1: Chase math (`chase.ts`) — TDD

**Files:**
- Create: `src/ChaseStinger/chase.ts`
- Test: `src/ChaseStinger/chase.test.ts`

Pure math, no React/Remotion imports. Reuses `interp` from the existing `wipe.ts` (also pure) for clamped, eased interpolation.

- [ ] **Step 1: Write the failing tests** — `src/ChaseStinger/chase.test.ts`:

```ts
import {describe, it, expect} from 'vitest';
import {actorX, laneY} from './chase';

const base = {durationInFrames: 90, width: 3840, maxDelay: 24};

describe('actorX', () => {
  it('starts fully off the left edge before its delay', () => {
    expect(actorX({...base, actorSize: 150, delay: 0, frame: 0})).toBe(-150);
  });

  it('ends fully off the right edge by the last frame', () => {
    // delay 24 actor: span = 90-1-24 = 65; at frame 24+65 = 89 -> xEnd
    expect(actorX({...base, actorSize: 420, delay: 24, frame: 89})).toBeCloseTo(3840 + 420);
  });

  it('is monotonically non-decreasing over time', () => {
    let prev = -Infinity;
    for (let f = 0; f <= 90; f++) {
      const x = actorX({...base, actorSize: 150, delay: 0, frame: f});
      expect(x).toBeGreaterThanOrEqual(prev);
      prev = x;
    }
  });

  it('the ball (no delay) leads a trailing robot', () => {
    const ball = actorX({...base, actorSize: 150, delay: 0, frame: 30});
    const robot = actorX({...base, actorSize: 420, delay: 8, frame: 30});
    expect(ball).toBeGreaterThan(robot);
  });
});

describe('laneY', () => {
  it('sits at centre+offset when the bob phase is zero', () => {
    expect(
      laneY({centerY: 1080, laneOffset: 120, frame: 0, bobAmplitude: 24, bobSpeed: 0.22, bobPhase: 0}),
    ).toBeCloseTo(1200);
  });

  it('never deviates more than the bob amplitude', () => {
    for (let f = 0; f <= 90; f++) {
      const y = laneY({centerY: 1080, laneOffset: 0, frame: f, bobAmplitude: 24, bobSpeed: 0.22, bobPhase: 1});
      expect(Math.abs(y - 1080)).toBeLessThanOrEqual(24 + 1e-9);
    }
  });
});
```

- [ ] **Step 2: Run tests, verify they fail** — `npm run test`. Expected: FAIL (cannot resolve `./chase`). Existing 12 tests still pass.

- [ ] **Step 3: Implement** — `src/ChaseStinger/chase.ts`:

```ts
import {interp} from '../Stinger/wipe';

export interface ActorXArgs {
  frame: number;
  durationInFrames: number;
  width: number; // composition width (px)
  actorSize: number; // actor diameter (px) — used for off-screen margins
  delay: number; // frames this actor lags behind the lead (the ball)
  maxDelay: number; // largest delay among all actors (so the last one still exits by the end)
}

// Horizontal centre (px) of an actor traveling left -> right and exiting off the right.
// Before `delay` it sits fully off the left edge; by frame (delay + span) it is fully off the right.
export const actorX = ({
  frame,
  durationInFrames,
  width,
  actorSize,
  delay,
  maxDelay,
}: ActorXArgs): number => {
  const xStart = -actorSize; // fully off the left edge
  const xEnd = width + actorSize; // fully off the right edge
  const span = Math.max(1, durationInFrames - 1 - maxDelay);
  // interp clamps to the range and applies easeInOut.
  return interp(frame - delay, [0, span], [xStart, xEnd]);
};

export interface LaneYArgs {
  centerY: number; // composition vertical centre (px)
  laneOffset: number; // this actor's lane offset from centre (px)
  frame: number;
  bobAmplitude: number; // vertical bob size (px)
  bobSpeed: number; // radians per frame
  bobPhase: number; // per-actor phase so they don't bob in unison
}

// Vertical centre (px) of an actor: its lane plus a gentle sinusoidal bob.
export const laneY = ({
  centerY,
  laneOffset,
  frame,
  bobAmplitude,
  bobSpeed,
  bobPhase,
}: LaneYArgs): number => centerY + laneOffset + bobAmplitude * Math.sin(frame * bobSpeed + bobPhase);
```

- [ ] **Step 4: Run tests, verify pass** — `npm run test`. Expected: all pass (12 existing + 6 new).

- [ ] **Step 5: Commit** — SKIP (no git for this project).

---

## Task 2: Schema + constants — TDD (light)

**Files:**
- Create: `src/ChaseStinger/constants.ts`
- Create: `src/ChaseStinger/schema.ts`
- Test: `src/ChaseStinger/schema.test.ts`

- [ ] **Step 1: Write the failing test** — `src/ChaseStinger/schema.test.ts`:

```ts
import {describe, it, expect} from 'vitest';
import {chaseStingerSchema} from './schema';
import {DEFAULT_ROBOTS} from './constants';

describe('chaseStingerSchema', () => {
  it('parses props with the default robots', () => {
    const parsed = chaseStingerSchema.parse({
      direction: 'right',
      panelColors: ['#0e0e12', '#7c3aed'],
      stagger: 4,
      holdFrames: 10,
      robots: DEFAULT_ROBOTS,
      trail: 8,
    });
    expect(parsed.robots.length).toBe(3);
    expect(parsed.robots[0].idDots).toHaveLength(4);
  });

  it('rejects a robot whose idDots is not a 4-tuple', () => {
    expect(() =>
      chaseStingerSchema.parse({
        direction: 'right',
        panelColors: ['#000000'],
        stagger: 4,
        holdFrames: 10,
        robots: [{teamColor: '#1e64ff', idDots: ['#00d000', '#ff20c0']}],
        trail: 8,
      }),
    ).toThrow();
  });

  it('does not carry a title field (omitted from the base schema)', () => {
    expect('title' in chaseStingerSchema.shape).toBe(false);
  });
});
```

- [ ] **Step 2: Run tests, verify fail** — `npm run test`. Expected: FAIL (cannot resolve `./schema` / `./constants`).

- [ ] **Step 3: Implement constants** — `src/ChaseStinger/constants.ts`:

```ts
import {RobotConfig} from './schema';

// Team colours (centre dot) and ID-dot palette (corner markers).
const BLUE = '#1e64ff';
const YELLOW = '#ffd400';
const GREEN = '#00d000';
const PINK = '#ff20c0';

// 2 blue + 1 yellow, each with a distinct 4-dot ID pattern.
export const DEFAULT_ROBOTS: RobotConfig[] = [
  {teamColor: BLUE, idDots: [GREEN, PINK, GREEN, PINK]},
  {teamColor: BLUE, idDots: [PINK, GREEN, GREEN, PINK]},
  {teamColor: YELLOW, idDots: [GREEN, GREEN, PINK, PINK]},
];

// Rendered sizes (px) on the 3840x2160 canvas.
export const ROBOT_SIZE = 420;
export const BALL_SIZE = 150;
export const BOB_AMPLITUDE = 24;
export const BOB_SPEED = 0.22;
```

- [ ] **Step 4: Implement schema** — `src/ChaseStinger/schema.ts`:

```ts
import {z} from 'zod';
import {zColor} from '@remotion/zod-types';
import {stingerSchema} from '../Stinger/schema';

export const robotSchema = z.object({
  teamColor: zColor(), // centre dot
  idDots: z.tuple([zColor(), zColor(), zColor(), zColor()]), // FL, FR, RL, RR
});

export type RobotConfig = z.infer<typeof robotSchema>;

// Reuse the wipe knobs (minus title), add the robot roster and chase trail.
export const chaseStingerSchema = stingerSchema.omit({title: true}).extend({
  robots: z.array(robotSchema).min(1),
  trail: z.number().int().min(0).max(30), // frames each successive robot lags the ball
});
```

- [ ] **Step 5: Run tests, verify pass** — `npm run test`. Expected: all pass (existing + new schema tests).

- [ ] **Step 6: Commit** — SKIP (no git).

---

## Task 3: Robot and Ball components

**Files:**
- Create: `src/ChaseStinger/RobotTop.tsx`
- Create: `src/ChaseStinger/Ball.tsx`

Verified observationally in Task 5/6 (components can't render without a composition).

- [ ] **Step 1: Implement `RobotTop.tsx`** — top-down robot from the verified SSL geometry, rotated so the flat front faces right (direction of travel):

```tsx
import React from 'react';

// Top-down RoboCup SSL robot. Geometry in mm (viewBox), 1:1 with the spec:
//   body R85 with a flat front (chord at y=-55, corners x=±64.807),
//   centre dot r25 (team colour), four ID dots r20 at radius 65.
// rotate(90) turns the pattern's front (top) to face right.
export const RobotTop: React.FC<{
  size: number; // rendered width/height (px)
  teamColor: string; // centre dot
  idDots: [string, string, string, string]; // FL, FR, RL, RR
  bodyColor?: string;
}> = ({size, teamColor, idDots, bodyColor = '#1a1a1e'}) => {
  const [fl, fr, rl, rr] = idDots;
  return (
    <svg width={size} height={size} viewBox="-85 -85 170 170" style={{display: 'block'}}>
      <g transform="rotate(90)">
        <path d="M -64.807 -55 L 64.807 -55 A 85 85 0 1 1 -64.807 -55 Z" fill={bodyColor} />
        <circle cx="0" cy="0" r="25" fill={teamColor} />
        <circle cx="-54.772" cy="-35" r="20" fill={fl} />
        <circle cx="54.772" cy="-35" r="20" fill={fr} />
        <circle cx="-35" cy="54.772" r="20" fill={rl} />
        <circle cx="35" cy="54.772" r="20" fill={rr} />
      </g>
    </svg>
  );
};
```

- [ ] **Step 2: Implement `Ball.tsx`** — orange SSL ball with a soft highlight (note JSX `stopColor`, not `stop-color`):

```tsx
import React from 'react';

export const Ball: React.FC<{size: number}> = ({size}) => (
  <svg width={size} height={size} viewBox="-50 -50 100 100" style={{display: 'block'}}>
    <defs>
      <radialGradient id="ssl-ball" cx="38%" cy="35%" r="75%">
        <stop offset="0%" stopColor="#ffb24d" />
        <stop offset="45%" stopColor="#ff7a00" />
        <stop offset="100%" stopColor="#d65a00" />
      </radialGradient>
    </defs>
    <circle cx="0" cy="0" r="48" fill="url(#ssl-ball)" />
    <circle cx="-16" cy="-18" r="9" fill="#ffffff" opacity="0.55" />
  </svg>
);
```

- [ ] **Step 3: Type-check** — `npx tsc --noEmit`. Expected: no errors.

- [ ] **Step 4: Commit** — SKIP (no git).

---

## Task 4: Chase layer

**Files:**
- Create: `src/ChaseStinger/ChaseLayer.tsx`

- [ ] **Step 1: Implement `ChaseLayer.tsx`** — positions ball + robots from `chase.ts`:

```tsx
import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {actorX, laneY} from './chase';
import {RobotTop} from './RobotTop';
import {Ball} from './Ball';
import {RobotConfig} from './schema';
import {ROBOT_SIZE, BALL_SIZE, BOB_AMPLITUDE, BOB_SPEED} from './constants';

// Vertical lane offset (px from centre) for each robot, so they spread out and
// don't perfectly overlap. Falls back to a spread for rosters longer than 3.
const robotLaneOffset = (i: number): number => [-280, 120, 340][i] ?? i * 200 - 200;

const place = (
  key: string,
  x: number,
  y: number,
  size: number,
  child: React.ReactNode,
): React.ReactNode => (
  <div
    key={key}
    style={{
      position: 'absolute',
      left: x,
      top: y,
      width: size,
      height: size,
      transform: 'translate(-50%, -50%)',
    }}
  >
    {child}
  </div>
);

export const ChaseLayer: React.FC<{robots: RobotConfig[]; trail: number}> = ({robots, trail}) => {
  const frame = useCurrentFrame();
  const {width, height, durationInFrames} = useVideoConfig();
  const centerY = height / 2;
  const maxDelay = robots.length * trail;

  const ballX = actorX({frame, durationInFrames, width, actorSize: BALL_SIZE, delay: 0, maxDelay});
  const ballY = laneY({
    centerY,
    laneOffset: -40,
    frame,
    bobAmplitude: BOB_AMPLITUDE,
    bobSpeed: BOB_SPEED,
    bobPhase: 0,
  });

  return (
    <AbsoluteFill>
      {robots.map((r, i) => {
        const delay = (i + 1) * trail;
        const x = actorX({frame, durationInFrames, width, actorSize: ROBOT_SIZE, delay, maxDelay});
        const y = laneY({
          centerY,
          laneOffset: robotLaneOffset(i),
          frame,
          bobAmplitude: BOB_AMPLITUDE,
          bobSpeed: BOB_SPEED,
          bobPhase: i + 1,
        });
        return place(`r${i}`, x, y, ROBOT_SIZE, <RobotTop size={ROBOT_SIZE} teamColor={r.teamColor} idDots={r.idDots} />);
      })}
      {place('ball', ballX, ballY, BALL_SIZE, <Ball size={BALL_SIZE} />)}
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: Type-check** — `npx tsc --noEmit`. Expected: no errors.

- [ ] **Step 3: Commit** — SKIP (no git).

---

## Task 5: Composition + registration + scripts

**Files:**
- Create: `src/ChaseStinger/ChaseStinger.tsx`
- Modify: `src/Root.tsx`
- Modify: `package.json`

- [ ] **Step 1: Implement `ChaseStinger.tsx`** — transparent root, reused `Panels` wipe, chase layer on top:

```tsx
import React from 'react';
import {z} from 'zod';
import {AbsoluteFill} from 'remotion';
import {chaseStingerSchema} from './schema';
import {Panels} from '../Stinger/Panels';
import {ChaseLayer} from './ChaseLayer';

export const ChaseStinger: React.FC<z.infer<typeof chaseStingerSchema>> = ({
  direction,
  panelColors,
  stagger,
  holdFrames,
  robots,
  trail,
}) => {
  return (
    <AbsoluteFill>
      <Panels colors={panelColors} direction={direction} stagger={stagger} holdFrames={holdFrames} />
      <ChaseLayer robots={robots} trail={trail} />
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: Modify `src/Root.tsx`** — register a second composition. The file currently registers only `Stinger`. Replace its contents with:

```tsx
import React from 'react';
import {Composition} from 'remotion';
import {Stinger} from './Stinger/Stinger';
import {stingerSchema} from './Stinger/schema';
import {ChaseStinger} from './ChaseStinger/ChaseStinger';
import {chaseStingerSchema} from './ChaseStinger/schema';
import {DEFAULT_ROBOTS} from './ChaseStinger/constants';
import {DIMENSIONS, FPS, DURATION, DEFAULT_PALETTE} from './Stinger/constants';

export const RemotionRoot: React.FC = () => {
  return (
    <>
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
      <Composition
        id="ChaseStinger"
        component={ChaseStinger}
        durationInFrames={DURATION}
        fps={FPS}
        width={DIMENSIONS.width}
        height={DIMENSIONS.height}
        schema={chaseStingerSchema}
        defaultProps={{
          direction: 'right' as const,
          panelColors: DEFAULT_PALETTE,
          stagger: 4,
          holdFrames: 10,
          robots: DEFAULT_ROBOTS,
          trail: 8,
        }}
      />
    </>
  );
};
```

- [ ] **Step 3: Modify `package.json`** — add two scripts to the `"scripts"` block (leave the others intact):

```json
    "render:chase": "remotion render ChaseStinger out/chase-stinger.webm --codec=vp9 --image-format=png",
    "render:chase:preview": "remotion render ChaseStinger out/chase-stinger-preview.webm --codec=vp9 --image-format=png --scale=0.25"
```

- [ ] **Step 4: Verify the composition registers** — `npx remotion compositions`. Expected: lists BOTH `Stinger` and `ChaseStinger` (each 3840x2160, 90 frames, 60fps).

- [ ] **Step 5: Type-check + tests** — `npx tsc --noEmit` (no errors) and `npm run test` (all pass).

- [ ] **Step 6: Commit** — SKIP (no git).

---

## Task 6: Render, verify alpha + readability, README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Render a fast preview** — `npm run render:chase:preview`. Expected: produces `out/chase-stinger-preview.webm` (960x540), no errors.

- [ ] **Step 2: Verify alpha** — `npx remotion ffprobe out/chase-stinger-preview.webm | grep alpha_mode`. Expected: `alpha_mode : 1`.

- [ ] **Step 3: Add a README section** — append to `README.md`:

````markdown

## ChaseStinger variant

`ChaseStinger` is the same panel wipe with a top-down RoboCup scene on top: an
orange ball streaks left→right with three robots (2 blue + 1 yellow, distinct IDs)
chasing it, the pack crossing centre during the covered hold.

```bash
npm run render:chase           # full 4K -> out/chase-stinger.webm
npm run render:chase:preview   # fast 960x540 sanity check
```

Extra Studio knobs (on top of the wipe controls): `robots` (each with a team
centre-dot colour + four ID-dot colours; array length = how many chase) and
`trail` (frames each successive robot lags behind the ball). Use it in OBS exactly
like the base stinger (transition point 750 ms).
````

- [ ] **Step 4: Commit** — SKIP (no git). The full 4K render (`npm run render:chase`) is run separately by the controller.

---

## Done

`ChaseStinger` renders alongside `Stinger`: a transparent VP9 stinger with the panel wipe plus three robots chasing an orange ball. Chase math is unit-tested; transparency and readability verified via render + browser composite.
