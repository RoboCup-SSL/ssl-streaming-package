import React from 'react';
import {AbsoluteFill} from 'remotion';
import {RobotTop} from '../ChaseStinger/RobotTop';
import {type RobotCompositionProps} from './schema';

// Standalone composition: just the SSL robot (the same geometry the chase stingers
// use) centred on a TRANSPARENT canvas (no root backgroundColor — the transparency
// invariant applies here). Renders to a single PNG you drop into OBS and scale freely.
export const Robot: React.FC<RobotCompositionProps> = ({
  teamColor,
  idDots,
  bodyColor,
  size,
  orientation,
}) => {
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
      <RobotTop
        size={size}
        teamColor={teamColor}
        idDots={idDots}
        bodyColor={bodyColor}
        orientation={orientation}
      />
    </AbsoluteFill>
  );
};
