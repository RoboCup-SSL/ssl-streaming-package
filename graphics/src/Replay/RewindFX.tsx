import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {trackingBarY} from './frame';
import {BRAND, REWIND} from '../theme';

// A left-pointing triangle (CSS borders) — half of the ◄◄ rewind glyph.
const Tri: React.FC = () => (
  <span
    style={{
      width: 0,
      height: 0,
      borderTop: '32px solid transparent',
      borderBottom: '32px solid transparent',
      borderRight: `50px solid ${BRAND.magenta}`,
    }}
  />
);

// VHS "rewind" overlay: scanlines + a vertically-rolling tracking bar + a blinking
// ◄◄ REWIND glyph. Semi-transparent, so over the live feed (pre-roll/reveal) it reads
// as a tape being shuttled, and over the opaque cover it only tints (coverage intact).
export const RewindFX: React.FC = () => {
  const frame = useCurrentFrame();
  const {height} = useVideoConfig();
  const barY = trackingBarY(frame, height, REWIND.barHeight, REWIND.barSpeed);
  const blink = frame % 32 < 26 ? 1 : 0.3; // OSD-style flicker

  return (
    <AbsoluteFill>
      {/* scanlines */}
      <AbsoluteFill
        style={{
          backgroundImage: `repeating-linear-gradient(to bottom, rgba(0,0,0,${REWIND.scanlineOpacity}) 0px, rgba(0,0,0,${REWIND.scanlineOpacity}) ${REWIND.scanlineThickness}px, transparent ${REWIND.scanlineThickness}px, transparent ${REWIND.scanlineGap}px)`,
        }}
      />
      {/* rolling tracking bar */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: barY,
          height: REWIND.barHeight,
          background:
            'linear-gradient(to bottom, rgba(255,255,255,0) 0%, rgba(255,255,255,0.10) 35%, rgba(255,255,255,0.30) 50%, rgba(255,255,255,0.10) 65%, rgba(255,255,255,0) 100%)',
          filter: 'blur(3px)',
        }}
      />
      {/* ◄◄ REWIND glyph */}
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 28,
            background: BRAND.ink,
            color: '#ffffff',
            padding: '24px 56px',
            borderRadius: 18,
            fontFamily: 'sans-serif',
            fontSize: 88,
            fontWeight: 800,
            letterSpacing: 10,
            opacity: blink,
            boxShadow: '0 10px 40px rgba(0,0,0,0.45)',
          }}
        >
          <span style={{display: 'flex', gap: 8}}>
            <Tri />
            <Tri />
          </span>
          REWIND
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
