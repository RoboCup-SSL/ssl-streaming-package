import React from 'react';
import {AbsoluteFill, Img, staticFile} from 'remotion';
import {standbySchema, type StandbyProps} from './schema';
import {BreathingBackground} from './BreathingBackground';
import {NextMatchBlock} from './NextMatch';
import {BRAND, STANDBY, ASSETS} from '../theme';

// Full-screen OPAQUE "next match in …" holding scene — the thin COMBO that stacks the
// reusable pieces: the breathing background + the next-match block, plus holding-screen
// decoration (logo + mascot) that belongs only here (you don't want the big mascot in a
// webcam corner). Unlike the stingers/overlays the root intentionally carries a
// backgroundColor (paper) — the documented exception to the transparency invariant.
//
// The live countdown number is supplied by OBS over the block's reserved slot; only the
// fixed label/sublabel are baked in. No fades anywhere: flat colour, hard edges.
export const Standby: React.FC<StandbyProps> = ({
  label,
  sublabel,
  bands,
  loopDuration,
  showSlotGuide,
}) => {
  return (
    <AbsoluteFill style={{backgroundColor: BRAND.paper, fontFamily: 'sans-serif'}}>
      <BreathingBackground bands={bands} loopDuration={loopDuration} />

      {/* Wordmark — white logo on a solid dark chip (no shadow). */}
      <div
        style={{
          position: 'absolute',
          top: 56,
          left: 72,
          background: BRAND.ink,
          borderRadius: 14,
          padding: '16px 28px',
          display: 'flex',
          alignItems: 'center',
        }}
      >
        <Img src={staticFile(ASSETS.logo)} style={{height: 40, display: 'block'}} />
      </div>

      {/* Mascot — right side, STATIC (no bob), flat (no drop-shadow). */}
      <Img
        src={staticFile(ASSETS.mascot)}
        style={{
          position: 'absolute',
          right: '4%',
          bottom: 0,
          height: STANDBY.mascotHeight,
        }}
      />

      {/* The next-match block, positioned at the holding-screen spot (left-centre). */}
      <AbsoluteFill
        style={{justifyContent: 'center', alignItems: 'flex-start', paddingLeft: 120}}
      >
        <NextMatchBlock label={label} sublabel={sublabel} showSlotGuide={showSlotGuide} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

export {standbySchema};
