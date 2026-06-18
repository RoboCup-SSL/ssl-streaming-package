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
      for (const frame of [40, 41, 45, 49]) {
        expect(panelOffset({...base, panelIndex, frame})).toBe(0);
      }
    }
  });

  it('panel 0 is fully off the trailing edge at the last frame', () => {
    expect(panelOffset({...base, panelIndex: 0, frame: 90})).toBeCloseTo(100);
  });

  it('panel 0 is halfway-eased through the cover phase at the midpoint', () => {
    // frame 20 of [0,40] => t=0.5 => easeInOut(0.5)=0.5 => lerp(-100,0,0.5) = -50
    expect(panelOffset({...base, panelIndex: 0, frame: 20})).toBeCloseTo(-50);
  });

  it('panel 0 is fully off the trailing edge on the last rendered frame', () => {
    expect(panelOffset({...base, panelIndex: 0, frame: 89})).toBeCloseTo(100);
  });

  it('with holdFrames=0 the panel covers exactly at the midpoint then immediately reveals', () => {
    // duration 90, hold 0 => coverEnd = revealStart = 45
    expect(panelOffset({durationInFrames: 90, holdFrames: 0, stagger: 4, panelIndex: 0, frame: 45})).toBe(0);
    expect(panelOffset({durationInFrames: 90, holdFrames: 0, stagger: 4, panelIndex: 0, frame: 46})).toBeGreaterThan(0);
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
