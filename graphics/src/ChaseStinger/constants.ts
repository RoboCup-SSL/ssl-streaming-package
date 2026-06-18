import type {RobotConfig} from './schema';

const BLUE = '#1e64ff';
const YELLOW = '#ffd400';
const GREEN = '#00d000';
const PINK = '#ff20c0';

// 3 blue + 3 yellow, each with a distinct 4-dot ID pattern.
export const DEFAULT_ROBOTS: RobotConfig[] = [
  {teamColor: BLUE, idDots: [GREEN, PINK, GREEN, PINK]},
  {teamColor: YELLOW, idDots: [PINK, GREEN, GREEN, PINK]},
  {teamColor: BLUE, idDots: [GREEN, GREEN, PINK, PINK]},
  {teamColor: YELLOW, idDots: [PINK, GREEN, PINK, GREEN]},
  {teamColor: BLUE, idDots: [GREEN, PINK, PINK, GREEN]},
  {teamColor: YELLOW, idDots: [PINK, PINK, GREEN, GREEN]},
];

// Rendered sizes (px) on the 3840x2160 canvas.
export const ROBOT_SIZE = 420;
export const BALL_SIZE = 150;
export const BOB_AMPLITUDE = 24;
export const BOB_SPEED = 0.22;
