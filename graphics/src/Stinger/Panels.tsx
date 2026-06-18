import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {Direction, panelOffset, offsetToTransform} from './wipe';

// Renders one full-screen colored layer per color. Layers are stacked in array
// order (last color on top). Each layer sweeps across using the pure wipe math.
export const Panels: React.FC<{
  colors: string[];
  direction: Direction;
  stagger: number;
  holdFrames: number;
  windowFrames?: number;
}> = ({colors, direction, stagger, holdFrames, windowFrames}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const total = windowFrames ?? durationInFrames;

  return (
    <>
      {colors.map((color, panelIndex) => {
        const percent = panelOffset({
          frame,
          durationInFrames: total,
          holdFrames,
          panelIndex,
          stagger,
        });
        return (
          <AbsoluteFill
            key={panelIndex}
            style={{
              backgroundColor: color,
              transform: offsetToTransform(percent, direction),
            }}
          />
        );
      })}
    </>
  );
};
