// Seamless 0..1 pulse for the REPLAY dot. `period` should divide the loop length.
export const pulse = ({frame, period}: {frame: number; period: number}): number =>
  0.5 + 0.5 * Math.sin((2 * Math.PI * frame) / period);

// Deterministic pseudo-random in [0, 1) from an integer seed. No Math.random — frames
// render in parallel and must be a pure function of the frame.
export const hashNoise = (seed: number): number => {
  const x = Math.sin(seed * 127.1) * 43758.5453;
  return x - Math.floor(x);
};

// Horizontal VHS tape-jitter (px) for a frame, in [-amplitude, amplitude].
export const jitterX = (frame: number, amplitude: number): number =>
  (hashNoise(frame) - 0.5) * 2 * amplitude;

// Vertical top (px) of a tracking bar of height `barHeight` rolling UPWARD across a
// screen of height `H` at `speed` px/frame; wraps seamlessly.
export const trackingBarY = (frame: number, H: number, barHeight: number, speed: number): number => {
  const period = H + barHeight;
  const p = (((frame * speed) % period) + period) % period;
  return H - p;
};
