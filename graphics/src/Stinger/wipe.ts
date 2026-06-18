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
  // Degenerate/inverted range: nothing to interpolate. Returns the high endpoint
  // once value reaches inMax, else the low endpoint. (panelOffset never hits this
  // with an inverted range; it's a safety backstop.)
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
//   cover   frames 0..coverEnd            panels slide -100 -> 0
//   hold    frames coverEnd..revealStart  all panels held at 0 (screen covered)
//   reveal  frames revealStart..duration  panels slide 0 -> 100
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
  return interp(frame, [exitStart, durationInFrames - 1], [0, 100]);
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
