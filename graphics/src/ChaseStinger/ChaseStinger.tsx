import React from 'react';
import {z} from 'zod';
import {AbsoluteFill, Sequence, useVideoConfig} from 'remotion';
import {chaseStingerSchema} from './schema';
import {Panels} from '../Stinger/Panels';
import {ChaseLayer} from './ChaseLayer';

export const ChaseStinger: React.FC<z.infer<typeof chaseStingerSchema>> = ({
  direction,
  panelColors,
  stagger,
  holdFrames,
  robots,
  trail,
  scouts,
  wipeDelay,
  reverse,
}) => {
  const {durationInFrames} = useVideoConfig();
  return (
    <AbsoluteFill>
      {/* Scouts drive across the transparent screen during the wipeDelay pre-roll,
          then the wipe sweeps in. windowFrames tells Panels to complete within the
          remaining frames (its useCurrentFrame is shifted by the Sequence). */}
      <Sequence from={wipeDelay}>
        <Panels
          colors={panelColors}
          direction={direction}
          stagger={stagger}
          holdFrames={holdFrames}
          windowFrames={durationInFrames - wipeDelay}
        />
      </Sequence>
      <ChaseLayer robots={robots} trail={trail} scouts={scouts} reverse={reverse} />
    </AbsoluteFill>
  );
};
