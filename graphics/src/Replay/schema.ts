import {z} from 'zod';
import {zColor} from '@remotion/zod-types';

export const replayOverlaySchema = z.object({
  bands: z.array(zColor()).min(1),
  frameThickness: z.number().int().min(2).max(400),
  label: z.string(),
});
