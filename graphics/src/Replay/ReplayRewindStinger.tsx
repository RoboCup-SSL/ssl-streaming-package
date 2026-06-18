import React from 'react';
import {z} from 'zod';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {chaseStingerSchema} from '../ChaseStinger/schema';
import {ChaseStinger} from '../ChaseStinger/ChaseStinger';
import {RewindFX} from './RewindFX';
import {jitterX} from './frame';
import {REWIND} from '../theme';

// The live -> replay transition: the reverse robot chase (robots roll right->left
// while facing right) under a VHS "rewind" overlay. The chase is jittered + slightly
// overscanned so the horizontal tape-jitter never exposes a transparent edge during
// the coverage hold; the FX overlay sits on top, unjittered.
export const ReplayRewindStinger: React.FC<z.infer<typeof chaseStingerSchema>> = (props) => {
  const frame = useCurrentFrame();
  const jx = jitterX(frame, REWIND.jitter);

  return (
    <AbsoluteFill>
      <AbsoluteFill style={{transform: `translateX(${jx}px) scale(${REWIND.overscan})`}}>
        <ChaseStinger {...props} reverse />
      </AbsoluteFill>
      <RewindFX />
    </AbsoluteFill>
  );
};
