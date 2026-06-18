import React from 'react';

// Top-down RoboCup SSL robot. Geometry in mm (viewBox), 1:1 with the spec:
//   body R85 with a flat front (chord at y=-55, corners x=±64.807),
//   centre dot r25 (team colour), four ID dots r20 at radius 65.
// rotate(90) turns the pattern's front (top) to face right (direction of travel).
export const RobotTop: React.FC<{
  size: number; // rendered width/height (px)
  teamColor: string; // centre dot
  idDots: [string, string, string, string]; // FL, FR, RL, RR
  bodyColor?: string;
}> = ({size, teamColor, idDots, bodyColor = '#1a1a1e'}) => {
  const [fl, fr, rl, rr] = idDots;
  return (
    <svg width={size} height={size} viewBox="-85 -85 170 170" style={{display: 'block'}}>
      <g transform="rotate(90)">
        <path d="M -64.807 -55 L 64.807 -55 A 85 85 0 1 1 -64.807 -55 Z" fill={bodyColor} />
        <circle cx="0" cy="0" r="25" fill={teamColor} />
        <circle cx="-54.772" cy="-35" r="20" fill={fl} />
        <circle cx="54.772" cy="-35" r="20" fill={fr} />
        <circle cx="-35" cy="54.772" r="20" fill={rl} />
        <circle cx="35" cy="54.772" r="20" fill={rr} />
      </g>
    </svg>
  );
};
