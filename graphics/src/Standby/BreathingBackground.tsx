import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {bandBoundaries} from './standby';
import {type BreathingBackgroundProps} from './schema';
import {BRAND, STANDBY} from '../theme';

// Thick vertical colour bars (one per `bands` colour) lined up left->right to tile a
// big square field, the whole field tilted by `bandAngle`. A breathing wave makes the
// shared boundaries slide continuously, so the focused colour bulges wider while its
// neighbours yield their facing edge — no overlap, no z-index, hard edges, no fades,
// and (because every edge is a continuous function of the frame) no jumps.
//
// OPAQUE (paper root) and full-screen: a reusable backdrop. Render it standalone as a
// looping MP4 to sit behind a webcam, or let `Standby` stack the next-match block on it.
export const BreathingBackground: React.FC<BreathingBackgroundProps> = ({bands, loopDuration}) => {
  const frame = useCurrentFrame();
  const n = bands.length;

  // Square field big enough to still cover 1920×1080 after the tilt.
  const fieldSize = 2600;
  const bounds = bandBoundaries(
    frame,
    loopDuration,
    STANDBY.restFrames,
    n,
    STANDBY.breathAmplitude,
    STANDBY.breathReach,
    fieldSize,
    STANDBY.breathGain,
  );

  return (
    <AbsoluteFill style={{backgroundColor: BRAND.paper, overflow: 'hidden'}}>
      <div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          width: fieldSize,
          height: fieldSize,
          transform: `translate(-50%, -50%) rotate(${STANDBY.bandAngle}deg)`,
        }}
      >
        {bands.map((color, i) => {
          const left = bounds[i];
          // +1px so adjacent bars never reveal a sub-pixel seam at the shared edge.
          const width = bounds[i + 1] - bounds[i] + 1;
          return (
            <div
              key={i}
              style={{
                position: 'absolute',
                top: 0,
                height: fieldSize,
                left,
                width,
                background: color,
              }}
            />
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
