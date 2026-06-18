import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {actorX, laneY} from './chase';
import {RobotTop} from './RobotTop';
import {Ball} from './Ball';
import {RobotConfig} from './schema';
import {ROBOT_SIZE, BALL_SIZE, BOB_AMPLITUDE, BOB_SPEED} from './constants';

// Vertical lane offsets (px from centre) for the pack. Sized to fit a 2160-tall
// canvas (robot 420 → keep |offset| under ~760). Falls back to a spread for big rosters.
const LANE_OFFSETS = [-200, 220, -520, 480, -60, 600];
const robotLaneOffset = (i: number): number => LANE_OFFSETS[i] ?? i * 180 - 450;

const place = (
  key: string,
  x: number,
  y: number,
  size: number,
  child: React.ReactNode,
): React.ReactNode => (
  <div
    key={key}
    style={{
      position: 'absolute',
      left: x,
      top: y,
      width: size,
      height: size,
      transform: 'translate(-50%, -50%)',
    }}
  >
    {child}
  </div>
);

export const ChaseLayer: React.FC<{
  robots: RobotConfig[];
  trail: number;
  scouts: number;
  reverse?: boolean;
}> = ({robots, trail, scouts, reverse}) => {
  const frame = useCurrentFrame();
  const {width, height, durationInFrames} = useVideoConfig();
  const centerY = height / 2;

  // Front-to-back delay order: scout robots (0..scouts-1), then the ball, then the
  // chasers. The ball occupies slot `scouts`, so chaser robots shift back by one.
  // Clamp scouts to the roster size so the ball can never be pushed past the last
  // slot (which would strand it mid-screen and never let it exit).
  const effectiveScouts = Math.min(scouts, robots.length);
  const maxDelay = robots.length * trail;
  const ballDelay = effectiveScouts * trail;

  const ballX = actorX({frame, durationInFrames, width, actorSize: BALL_SIZE, delay: ballDelay, maxDelay, reverse});
  const ballY = laneY({
    centerY,
    laneOffset: -40,
    frame,
    bobAmplitude: BOB_AMPLITUDE,
    bobSpeed: BOB_SPEED,
    bobPhase: 0,
  });

  return (
    <AbsoluteFill>
      {robots.map((r, i) => {
        const position = i < effectiveScouts ? i : i + 1;
        const delay = position * trail;
        const x = actorX({frame, durationInFrames, width, actorSize: ROBOT_SIZE, delay, maxDelay, reverse});
        const y = laneY({
          centerY,
          laneOffset: robotLaneOffset(i),
          frame,
          bobAmplitude: BOB_AMPLITUDE,
          bobSpeed: BOB_SPEED,
          bobPhase: i + 1,
        });
        return place(`r${i}`, x, y, ROBOT_SIZE, <RobotTop size={ROBOT_SIZE} teamColor={r.teamColor} idDots={r.idDots} />);
      })}
      {place('ball', ballX, ballY, BALL_SIZE, <Ball size={BALL_SIZE} />)}
    </AbsoluteFill>
  );
};
