import React from 'react';
import {Composition} from 'remotion';
import {Stinger} from './Stinger/Stinger';
import {stingerSchema} from './Stinger/schema';
import {ChaseStinger} from './ChaseStinger/ChaseStinger';
import {chaseStingerSchema} from './ChaseStinger/schema';
import {DEFAULT_ROBOTS} from './ChaseStinger/constants';
import {ReplayOverlay} from './Replay/ReplayOverlay';
import {ReplayRewindStinger} from './Replay/ReplayRewindStinger';
import {replayOverlaySchema} from './Replay/schema';
import {Standby} from './Standby/Standby';
import {BreathingBackground} from './Standby/BreathingBackground';
import {NextMatch} from './Standby/NextMatch';
import {standbySchema, breathingBackgroundSchema, nextMatchSchema} from './Standby/schema';
import {Robot} from './Robot/Robot';
import {robotCompositionSchema} from './Robot/schema';
import {FRAME, TIMING, BRAND_BARS, STANDBY} from './theme';
import {DIMENSIONS, FPS, DURATION, DEFAULT_PALETTE} from './Stinger/constants';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Stinger"
        component={Stinger}
        durationInFrames={DURATION}
        fps={FPS}
        width={DIMENSIONS.width}
        height={DIMENSIONS.height}
        schema={stingerSchema}
        defaultProps={{
          direction: 'right' as const,
          panelColors: DEFAULT_PALETTE,
          stagger: 4,
          holdFrames: 10,
          title: '',
        }}
      />
      <Composition
        id="ChaseStinger"
        component={ChaseStinger}
        durationInFrames={DURATION}
        fps={FPS}
        width={DIMENSIONS.width}
        height={DIMENSIONS.height}
        schema={chaseStingerSchema}
        defaultProps={{"direction":"right" as const,"panelColors":BRAND_BARS,"stagger":4,"holdFrames":10,"robots":[{"teamColor":"#1e64ff","idDots":["#00d000","#ff20c0","#00d000","#ff20c0"]},{"teamColor":"#ffd400","idDots":["#ff20c0","#00d000","#00d000","#ff20c0"]},{"teamColor":"#1e64ff","idDots":["#00d000","#00d000","#ff20c0","#ff20c0"]},{"teamColor":"#ffd400","idDots":["#ff20c0","#00d000","#ff20c0","#00d000"]},{"teamColor":"#1e64ff","idDots":["#00d000","#ff20c0","#ff20c0","#00d000"]},{"teamColor":"#ffd400","idDots":["#ff20c0","#ff20c0","#00d000","#00d000"]}],"trail":6,"scouts":2,"wipeDelay":10,"reverse":false}}
      />
      <Composition
        id="ReplayOverlay"
        component={ReplayOverlay}
        durationInFrames={TIMING.loopDuration}
        fps={FPS}
        width={DIMENSIONS.width}
        height={DIMENSIONS.height}
        schema={replayOverlaySchema}
        defaultProps={{
          bands: BRAND_BARS,
          frameThickness: FRAME.thickness,
          label: 'REPLAY',
        }}
      />
      {/* live -> replay: robots roll right->left while facing right (a "rewind"),
          under a VHS tape-shuttle FX overlay. */}
      <Composition
        id="ReplayRewindStinger"
        component={ReplayRewindStinger}
        durationInFrames={TIMING.stingerDuration}
        fps={FPS}
        width={DIMENSIONS.width}
        height={DIMENSIONS.height}
        schema={chaseStingerSchema}
        defaultProps={{
          direction: 'left' as const,
          panelColors: BRAND_BARS,
          stagger: 4,
          holdFrames: TIMING.holdFrames,
          robots: DEFAULT_ROBOTS,
          trail: 6,
          scouts: 2,
          wipeDelay: 10,
          reverse: true,
        }}
      />
      {/* replay -> live: robots drive forward left->right (a "resume"). */}
      <Composition
        id="ReplayResumeStinger"
        component={ChaseStinger}
        durationInFrames={TIMING.stingerDuration}
        fps={FPS}
        width={DIMENSIONS.width}
        height={DIMENSIONS.height}
        schema={chaseStingerSchema}
        defaultProps={{
          direction: 'right' as const,
          panelColors: BRAND_BARS,
          stagger: 4,
          holdFrames: TIMING.holdFrames,
          robots: DEFAULT_ROBOTS,
          trail: 6,
          scouts: 2,
          wipeDelay: 10,
          reverse: false,
        }}
      />
      {/* Reusable OPAQUE breathing colour-bar backdrop. Loops; sits behind a webcam or
          under the next-match block. Authored natively at 1920×1080. */}
      <Composition
        id="BreathingBackground"
        component={BreathingBackground}
        durationInFrames={STANDBY.loopDuration}
        fps={FPS}
        width={1920}
        height={1080}
        schema={breathingBackgroundSchema}
        defaultProps={{
          bands: BRAND_BARS,
          loopDuration: STANDBY.loopDuration,
        }}
      />
      {/* Reusable TRANSPARENT "next match in" block on a compact canvas -> a PNG you drop
          over any background/webcam in OBS and scale/position freely. No motion. */}
      <Composition
        id="NextMatch"
        component={NextMatch}
        durationInFrames={1}
        fps={FPS}
        width={1000}
        height={640}
        schema={nextMatchSchema}
        defaultProps={{
          label: 'NEXT MATCH IN',
          sublabel: 'SECONDS',
          showSlotGuide: true,
        }}
      />
      {/* Full-screen OPAQUE "next match in …" holding scene — the thin COMBO of the two
          reusable pieces above (+ logo/mascot). Authored natively at 1920×1080; the live
          number is added in OBS. */}
      <Composition
        id="Standby"
        component={Standby}
        durationInFrames={STANDBY.loopDuration}
        fps={FPS}
        width={1920}
        height={1080}
        schema={standbySchema}
        defaultProps={{
          label: 'NEXT MATCH IN',
          sublabel: 'SECONDS',
          bands: BRAND_BARS,
          loopDuration: STANDBY.loopDuration,
          showSlotGuide: true,
        }}
      />
      {/* Just the SSL robot on a TRANSPARENT square canvas -> a PNG for OBS. Defaults
          to the blue, facing-up robot (matches assets/robot_top.svg). The robot geometry
          is the same RobotTop used by the chase stingers. */}
      <Composition
        id="Robot"
        component={Robot}
        durationInFrames={1}
        fps={FPS}
        width={1080}
        height={1080}
        schema={robotCompositionSchema}
        defaultProps={{
          teamColor: '#1e64ff',
          idDots: ['#00d000', '#ff20c0', '#00d000', '#ff20c0'] as [string, string, string, string],
          bodyColor: '#1a1a1e',
          size: 900,
          orientation: 'up' as const,
        }}
      />
    </>
  );
};
