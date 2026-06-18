import React from 'react';
import {z} from 'zod';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {replayOverlaySchema} from './schema';
import {FrameBorder} from './FrameBorder';
import {pulse} from './frame';
import {BRAND, TIMING} from '../theme';

export const ReplayOverlay: React.FC<z.infer<typeof replayOverlaySchema>> = ({
  bands,
  frameThickness,
  label,
}) => {
  const frame = useCurrentFrame();
  const p = pulse({frame, period: TIMING.pulsePeriod});
  const dotOpacity = 0.35 + 0.65 * p;
  const dotScale = 0.85 + 0.3 * p;

  const barThickness = bands.map(() => frameThickness);

  return (
    <AbsoluteFill>
      <FrameBorder
        segmentColors={bands}
        barThickness={barThickness}
        leftThickness={frameThickness}
        rightThickness={frameThickness}
      />
      {/* REPLAY badge centred just below the top bar. */}
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'flex-start'}}>
        <div
          style={{
            marginTop: frameThickness + 24,
            display: 'flex',
            alignItems: 'center',
            gap: 24,
            background: BRAND.ink,
            color: '#ffffff',
            padding: '18px 44px',
            borderRadius: 999,
            fontFamily: 'sans-serif',
            fontSize: 64,
            fontWeight: 800,
            letterSpacing: 6,
            boxShadow: '0 8px 30px rgba(0,0,0,0.35)',
          }}
        >
          <span
            style={{
              width: 36,
              height: 36,
              borderRadius: '50%',
              background: BRAND.magenta,
              opacity: dotOpacity,
              transform: `scale(${dotScale})`,
            }}
          />
          {label}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
