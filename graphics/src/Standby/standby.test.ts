import {describe, it, expect} from 'vitest';
import {breathFocus, bandSwell, bandBoundaries} from './standby';

// Per the project's visual-first rule, the automated tests cover the load-bearing
// invariants only: the loop seam (no jump when OBS restarts the loop), the boundary
// ordering (a swelling bar must never invert a neighbour), full coverage, and that
// the rest phase is genuinely neutral (all bars even).
describe('Standby breathing wave', () => {
  const loop = 1080;
  const rest = 120;
  const count = 5;
  const amp = 0.45;
  const reach = 1.6;
  const field = 2600;
  const gain = 1.6;
  const bounds = (f: number) =>
    bandBoundaries(f, loop, rest, count, amp, reach, field, gain);

  it('breathFocus returns to its start after one full loop', () => {
    expect(breathFocus(loop, loop, rest, count, reach)).toBeCloseTo(
      breathFocus(0, loop, rest, count, reach),
      6,
    );
  });

  it('every boundary returns to its start after one full loop (seamless)', () => {
    const a = bounds(0);
    const b = bounds(loop);
    a.forEach((v, i) => expect(b[i]).toBeCloseTo(v, 6));
  });

  it('boundaries stay strictly increasing every frame (no inverted/crossed bars)', () => {
    for (let f = 0; f < loop; f += 7) {
      const bs = bounds(f);
      for (let i = 1; i < bs.length; i++) {
        expect(bs[i]).toBeGreaterThan(bs[i - 1]);
      }
    }
  });

  it('outer edges are pinned to the field (full coverage, no gaps)', () => {
    for (let f = 0; f < loop; f += 31) {
      const bs = bounds(f);
      expect(bs[0]).toBe(0);
      expect(bs[bs.length - 1]).toBe(field);
    }
  });

  it('the rest phase is perfectly neutral (all bars even, zero swell)', () => {
    const breath = (loop - 2 * rest) / 2;
    const restFrame = breath + Math.floor(rest / 2); // middle of the first rest
    for (let i = 0; i < count; i++) {
      expect(bandSwell(restFrame, loop, rest, i, count, amp, reach)).toBeCloseTo(0, 6);
    }
    const bs = bounds(restFrame);
    const even = field / count;
    for (let i = 1; i < bs.length; i++) {
      expect(bs[i] - bs[i - 1]).toBeCloseTo(even, 6);
    }
  });

  it('the focused bar bulges wider than its resting width mid-breath', () => {
    const breath = (loop - 2 * rest) / 2;
    const bs = bounds(breath / 2); // mid first sweep -> focus near the middle bar
    const even = field / count;
    const widest = Math.max(
      ...Array.from({length: count}, (_, i) => bs[i + 1] - bs[i]),
    );
    expect(widest).toBeGreaterThan(even);
  });
});
