import {clamp, lerp} from '../Stinger/wipe';

export interface ActorXArgs {
  frame: number;
  durationInFrames: number;
  width: number;
  actorSize: number;
  delay: number;
  maxDelay: number;
  reverse?: boolean; // true = travel right -> left (the actor still faces right, i.e. "in reverse")
}

// Horizontal centre (px) of an actor. Default travels left -> right and exits off
// the right; with `reverse`, it travels right -> left (entering off the right,
// exiting off the left) — the actor keeps facing right, reading as "driving backwards".
export const actorX = ({frame, durationInFrames, width, actorSize, delay, maxDelay, reverse}: ActorXArgs): number => {
  const xStart = reverse ? width + actorSize : -actorSize;
  const xEnd = reverse ? -actorSize : width + actorSize;
  // span sized so the most-delayed actor (delay === maxDelay) reaches xEnd at the
  // last frame (durationInFrames - 1). Changing this breaks that guarantee.
  const span = Math.max(1, durationInFrames - 1 - maxDelay);
  // Constant-speed (linear) travel so robots drive in promptly rather than easing.
  const t = clamp((frame - delay) / span, 0, 1);
  return lerp(xStart, xEnd, t);
};

export interface LaneYArgs {
  centerY: number;
  laneOffset: number;
  frame: number;
  bobAmplitude: number;
  bobSpeed: number;
  bobPhase: number;
}

// Vertical centre (px): lane plus a gentle sinusoidal bob.
export const laneY = ({
  centerY,
  laneOffset,
  frame,
  bobAmplitude,
  bobSpeed,
  bobPhase,
}: LaneYArgs): number => centerY + laneOffset + bobAmplitude * Math.sin(frame * bobSpeed + bobPhase);
