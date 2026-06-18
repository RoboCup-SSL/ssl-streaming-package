import {BRAND_BARS} from '../theme';

export const DIMENSIONS = {width: 3840, height: 2160};
export const FPS = 60;
export const DURATION = 90; // 1.5 seconds at 60fps

// Default palette = the RoboCup 2026 brand motif (orange→green→lime→purple→magenta),
// so the base wipe reads as the signature big-bold-blocks look and matches every other
// graphic. The LAST colour is the topmost layer — the one that dominates during the
// covered hold (the OBS swap window).
export const DEFAULT_PALETTE = BRAND_BARS;
