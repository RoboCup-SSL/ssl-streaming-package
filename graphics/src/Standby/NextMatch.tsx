import React from 'react';
import {AbsoluteFill} from 'remotion';
import {type NextMatchProps} from './schema';
import {BRAND} from '../theme';

// The "next match in …" block on a SOLID paper panel (so dark type stays legible over a
// bright background or a busy webcam). Hard edges, no shadow, no fade. This is the only
// thing the block draws — it is canvas- and position-agnostic: it does NOT set a root
// background and does NOT position itself. Whoever renders it decides where it sits:
//   - the `NextMatch` composition centres it on a compact transparent canvas (-> PNG);
//   - the `Standby` composition drops it at the holding-screen position.
// The live countdown number is NOT baked — OBS overlays it on the reserved slot.
export const NextMatchBlock: React.FC<NextMatchProps> = ({label, sublabel, showSlotGuide}) => {
  return (
    <div
      style={{
        background: BRAND.paper,
        borderRadius: 28,
        padding: '56px 64px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-start',
        fontFamily: 'sans-serif',
      }}
    >
      <div
        style={{
          color: BRAND.ink,
          fontSize: 88,
          fontWeight: 800,
          letterSpacing: 4,
          textTransform: 'uppercase',
          lineHeight: 1,
        }}
      >
        {label}
      </div>

      {/* Reserved slot for the OBS countdown number (no digits baked in). */}
      <div
        style={{
          marginTop: 28,
          width: 480,
          height: 280,
          borderRadius: 20,
          border: showSlotGuide ? `4px dashed ${BRAND.ink}` : 'none',
          display: 'flex',
          alignItems: 'flex-end',
          justifyContent: 'center',
        }}
      >
        {/* Solid baseline so the OBS text source lines up cleanly. */}
        <div
          style={{
            width: 340,
            height: 8,
            borderRadius: 4,
            marginBottom: 26,
            background: BRAND.orange,
          }}
        />
      </div>

      {sublabel ? (
        <div
          style={{
            marginTop: 18,
            color: '#5a5a63',
            fontSize: 40,
            fontWeight: 700,
            letterSpacing: 8,
            textTransform: 'uppercase',
          }}
        >
          {sublabel}
        </div>
      ) : null}
    </div>
  );
};

// Standalone composition: the block centred on a TRANSPARENT canvas (no root
// backgroundColor — the transparency invariant applies here). Renders to a single PNG
// you drop over any background/webcam in OBS and scale/position freely.
export const NextMatch: React.FC<NextMatchProps> = (props) => {
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
      <NextMatchBlock {...props} />
    </AbsoluteFill>
  );
};
