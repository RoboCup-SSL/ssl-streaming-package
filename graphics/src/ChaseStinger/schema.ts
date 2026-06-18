import {z} from 'zod';
import {zColor} from '@remotion/zod-types';
import {stingerSchema} from '../Stinger/schema';

export const robotSchema = z.object({
  teamColor: zColor(), // centre dot
  idDots: z.tuple([zColor(), zColor(), zColor(), zColor()]), // FL, FR, RL, RR
});

export type RobotConfig = z.infer<typeof robotSchema>;

// Reuse the wipe knobs (minus title), add the robot roster and chase trail.
export const chaseStingerSchema = stingerSchema.omit({title: true}).extend({
  robots: z.array(robotSchema).min(1),
  // Frames each successive actor lags the one ahead (kept low so the pack clears the timeline).
  trail: z.number().int().min(0).max(15),
  // Number of lead "scout" robots that drive in ahead of the ball (and before the wipe).
  scouts: z.number().int().min(0).max(10),
  // Frames the purple wipe is delayed, giving the scouts a pre-roll on the transparent screen.
  wipeDelay: z.number().int().min(0).max(30),
  // true = actors travel right->left (facing right -> "driving backwards", a rewind feel).
  // Optional: omitted/undefined behaves as forward (left->right), so existing callers are unaffected.
  reverse: z.boolean().optional(),
});
