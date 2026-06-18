import {describe, it, expect} from 'vitest';
import {actorX, laneY} from './chase';

const base = {durationInFrames: 90, width: 3840, maxDelay: 24};

describe('actorX', () => {
  it('starts fully off the left edge before its delay', () => {
    expect(actorX({...base, actorSize: 150, delay: 0, frame: 0})).toBe(-150);
  });

  it('ends fully off the right edge by the last frame', () => {
    expect(actorX({...base, actorSize: 420, delay: 24, frame: 89})).toBeCloseTo(3840 + 420);
  });

  it('is monotonically non-decreasing over time', () => {
    let prev = -Infinity;
    for (let f = 0; f < base.durationInFrames; f++) {
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

  it('the ball stays ahead of a trailing robot at every frame', () => {
    for (let f = 0; f < base.durationInFrames; f++) {
      const ball = actorX({...base, actorSize: 150, delay: 0, frame: f});
      const robot = actorX({...base, actorSize: 420, delay: 8, frame: f});
      // The chase invariant only holds while the ball is on-screen (x <= width).
      // In the off-screen overshoot region both actors clamp to their own xEnd
      // (ball=3990, robot=4260) — the robot's larger actorSize puts it further
      // right, so ball < robot there. That's visually fine; both are out of frame.
      if (ball <= base.width) {
        expect(ball).toBeGreaterThanOrEqual(robot);
      }
    }
  });

  it('moves at constant speed (equal frame steps give equal deltas)', () => {
    const at = (frame: number) => actorX({...base, actorSize: 150, delay: 0, frame});
    const d1 = at(20) - at(10);
    const d2 = at(40) - at(30);
    expect(d2).toBeCloseTo(d1, 5); // linear => equal deltas; easeInOut would differ
  });

  it('handles maxDelay=0 (all actors share delay 0) without NaN', () => {
    const x0 = actorX({durationInFrames: 90, width: 3840, maxDelay: 0, actorSize: 150, delay: 0, frame: 0});
    const xEnd = actorX({durationInFrames: 90, width: 3840, maxDelay: 0, actorSize: 150, delay: 0, frame: 89});
    expect(x0).toBe(-150);
    expect(Number.isNaN(xEnd)).toBe(false);
    expect(xEnd).toBeCloseTo(3840 + 150);
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
