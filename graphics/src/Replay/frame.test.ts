import {describe, it, expect} from 'vitest';
import {pulse} from './frame';

describe('pulse — seamless loop', () => {
  it('returns the same value at frame 0 and at one full period', () => {
    expect(pulse({frame: 0, period: 120})).toBeCloseTo(pulse({frame: 120, period: 120}));
  });
});
