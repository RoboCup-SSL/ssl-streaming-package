import React from 'react';
import {z} from 'zod';
import {AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate} from 'remotion';
import {stingerSchema} from './schema';
import {Panels} from './Panels';

const TITLE_FADE_FRAMES = 4;

export const Stinger: React.FC<z.infer<typeof stingerSchema>> = ({
  direction,
  panelColors,
  stagger,
  holdFrames,
  title,
}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const coverEnd = (durationInFrames - holdFrames) / 2;
  const revealStart = coverEnd + holdFrames;

  // Title is visible only while the screen is covered (the hold window).
  // Short-circuit when holdFrames=0: coverEnd===revealStart would produce
  // duplicate keyframes, causing interpolate to throw "strictly increasing".
  const titleOpacity =
    holdFrames <= 0
      ? 0
      : interpolate(
          frame,
          [
            coverEnd - TITLE_FADE_FRAMES,
            coverEnd,
            revealStart,
            revealStart + TITLE_FADE_FRAMES,
          ],
          [0, 1, 1, 0],
          {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
        );

  return (
    <AbsoluteFill>
      <Panels
        colors={panelColors}
        direction={direction}
        stagger={stagger}
        holdFrames={holdFrames}
      />
      {title ? (
        <AbsoluteFill
          style={{justifyContent: 'center', alignItems: 'center', opacity: titleOpacity}}
        >
          <h1
            style={{
              color: 'white',
              fontFamily: 'sans-serif',
              fontSize: 220,
              fontWeight: 800,
              letterSpacing: -4,
              margin: 0,
            }}
          >
            {title}
          </h1>
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  );
};
