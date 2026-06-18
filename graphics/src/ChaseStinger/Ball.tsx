import React from 'react';

export const Ball: React.FC<{size: number}> = ({size}) => (
  <svg width={size} height={size} viewBox="-50 -50 100 100" style={{display: 'block'}}>
    <defs>
      <radialGradient id="ssl-ball" cx="38%" cy="35%" r="75%">
        <stop offset="0%" stopColor="#ffb24d" />
        <stop offset="45%" stopColor="#ff7a00" />
        <stop offset="100%" stopColor="#d65a00" />
      </radialGradient>
    </defs>
    <circle cx="0" cy="0" r="48" fill="url(#ssl-ball)" />
    <circle cx="-16" cy="-18" r="9" fill="#ffffff" opacity="0.55" />
  </svg>
);
