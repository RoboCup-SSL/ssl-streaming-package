import {z} from 'zod';
import {zColor} from '@remotion/zod-types';

// The reusable breathing colour-bar background, on its own.
export const breathingBackgroundSchema = z.object({
  // The full-brightness colours of the breathing background bars (one bar each).
  bands: z.array(zColor()).min(1),
  // Seamless loop length in frames (also the composition duration). This is just the
  // Studio slider range — the real value is DERIVED in `theme.STANDBY` (breath + rest),
  // so keep the ceiling comfortably above it (60s @ 60fps = 3600).
  loopDuration: z.number().int().min(30).max(3600),
});

// The compact, transparent "next match in" block, on its own.
export const nextMatchSchema = z.object({
  // Baked, styled wording above the number slot. Swap for "BACK SOON",
  // "KICKOFF IN", "STARTING SOON", … and re-render.
  label: z.string(),
  // Small baked wording under the number slot (may be empty).
  sublabel: z.string(),
  // Show a faint dashed guide box around the OBS number slot (helpful while
  // aligning the OBS text source; turn off for the final broadcast render).
  showSlotGuide: z.boolean(),
});

// The combined holding scene = background + the next-match block (+ logo/mascot).
export const standbySchema = breathingBackgroundSchema.merge(nextMatchSchema);

export type BreathingBackgroundProps = z.infer<typeof breathingBackgroundSchema>;
export type NextMatchProps = z.infer<typeof nextMatchSchema>;
export type StandbyProps = z.infer<typeof standbySchema>;
