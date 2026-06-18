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
  stagger: 4, // frames of left->right arrival delay between the 5 colour segments
  loopDuration: 120, // overlay loop length (2s)
  pulsePeriod: 120, // divides loopDuration -> seamless loop
};

// VHS "rewind" overlay look for the reverse stinger.
export const REWIND = {
  jitter: 10, // max horizontal tape-jitter (px)
  overscan: 1.03, // scale the jittered content so jitter never exposes a transparent edge
  scanlineGap: 6, // px period of the scanlines
  scanlineThickness: 2, // px dark line within each period
  scanlineOpacity: 0.22,
  barHeight: 260, // px height of the rolling tracking bar
  barSpeed: 24, // px/frame the tracking bar rolls upward
};

// Full-screen "next match in …" holding scene (opaque, authored natively at 1080p).
// Background is thick vertical colour bars (one per colour) lined up left->right and
// tilted; a breathing wave swells each bar in turn, ping-ponging left->right->left.
// Hard edges, no fades. The mascot stands still.
// Rhythm: breathe across (a "breath"), hold at neutral, breathe back, hold.
// Expressed in seconds × FPS so the intent is explicit; loopDuration is DERIVED from
// these, so the composition duration, render length and motion always stay in sync —
// change the seconds (or FPS) here and nothing else needs touching.
const STANDBY_BREATH_FRAMES = 14 * FPS; // one breath
const STANDBY_REST_FRAMES = 2 * FPS; // rest after each breath
export const STANDBY = {
  loopDuration: 2 * (STANDBY_BREATH_FRAMES + STANDBY_REST_FRAMES), // 2 breaths + 2 rests
  restFrames: STANDBY_REST_FRAMES,
  bandAngle: 15, // degrees the lined-up colour bars are tilted
  breathAmplitude: 0.45, // peak swell weight of the focused bar (0 = rest)
  breathReach: 1.6, // radius (bars) of each swell; also the rest margin
  breathGain: 1.6, // how far the swell pushes the shared boundary (bulge size)
  mascotHeight: 780, // px rendered mascot height (static)
};

// Static assets, served by Remotion from public/ (wired for future graphics).
export const ASSETS = {
  mascot: 'mascot_with_ball.png',
  logo: 'logo_w.png',
};

export const EASING = easeInOut;
