import {easeInOut, lerp} from '../Stinger/wipe';

// Pure animation math for the Standby holding scene. Every value is a pure
// function of the frame (no Date.now/random/timers) so frames render in parallel.

// Position of the "breathing" focus along the row of colour bars, in bar units.
// The loop is a 4-phase rhythm:
//   breathe left -> right  (sweep, eased)
//   rest          (restFrames, held off the right edge -> all bars neutral)
//   breathe right -> left  (sweep, eased)
//   rest          (restFrames, held off the left edge -> all bars neutral)
// Each sweep runs a touch PAST the outer bars (±`reach`) so the bars fully settle
// to neutral during the rests. easeInOut means each sweep starts/ends at zero
// velocity, matching the held rests — so the whole loop is smooth AND seamless
// (value and velocity match at the wrap).
export const breathFocus = (
  frame: number,
  loopDuration: number,
  restFrames: number,
  count: number,
  reach: number,
): number => {
  if (loopDuration <= 0 || count <= 1) {
    return 0;
  }
  const leftEdge = -reach;
  const rightEdge = count - 1 + reach;
  const breath = Math.max(1, (loopDuration - 2 * restFrames) / 2);

  let f = ((frame % loopDuration) + loopDuration) % loopDuration;
  if (f < breath) {
    return lerp(leftEdge, rightEdge, easeInOut(f / breath)); // left -> right
  }
  f -= breath;
  if (f < restFrames) {
    return rightEdge; // rest (neutral)
  }
  f -= restFrames;
  if (f < breath) {
    return lerp(rightEdge, leftEdge, easeInOut(f / breath)); // right -> left
  }
  return leftEdge; // rest (neutral)
};

// How much bar `index` is "breathing" right now: a raised-cosine bump in
// [0, amplitude], peaked on the focus and reaching exactly 0 at distance `reach`.
// The compact support (zero beyond `reach`) is what lets the rests be perfectly
// neutral once the focus sweeps `reach` past the outermost bar.
export const bandSwell = (
  frame: number,
  loopDuration: number,
  restFrames: number,
  index: number,
  count: number,
  amplitude: number,
  reach: number,
): number => {
  const focus = breathFocus(frame, loopDuration, restFrames, count, reach);
  const d = Math.abs(index - focus);
  if (d >= reach) {
    return 0;
  }
  return amplitude * 0.5 * (1 + Math.cos((Math.PI * d) / reach));
};

// The boundary positions (px, in field space) of `count` colour bars tiling a field
// of width `fieldWidth`. Returns count+1 positions: [0, b0, b1, …, fieldWidth].
//
// The two OUTER edges are fixed (0 and fieldWidth) so the field is always fully and
// exactly covered — no gaps, no overflow. Each INTERIOR boundary slides continuously
// off its resting midpoint toward whichever neighbour is breathing less, by an amount
// proportional to the swell difference. So a swelling bar bulges wider while its
// neighbours yield their facing edge — but every edge moves as a smooth, continuous
// function of the frame. No overlap, no z-index, hence NO jump. During a rest all
// swells are 0, so every boundary sits at its even resting midpoint.
export const bandBoundaries = (
  frame: number,
  loopDuration: number,
  restFrames: number,
  count: number,
  amplitude: number,
  reach: number,
  fieldWidth: number,
  gain: number,
): number[] => {
  const barWidth = fieldWidth / count;
  // Per-boundary shift is capped below barWidth/2 so neighbouring boundaries can
  // never cross (which would invert a bar). `gain` scales the visible bulge.
  const k = barWidth * 0.5 * gain;
  const swell = Array.from({length: count}, (_, i) =>
    bandSwell(frame, loopDuration, restFrames, i, count, amplitude, reach),
  );

  const bounds = [0];
  for (let i = 0; i < count - 1; i++) {
    const mid = (i + 1) * barWidth;
    bounds.push(mid + (swell[i] - swell[i + 1]) * k);
  }
  bounds.push(fieldWidth);
  return bounds;
};
