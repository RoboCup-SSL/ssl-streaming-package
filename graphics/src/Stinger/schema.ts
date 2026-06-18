import {z} from 'zod';
import {zColor} from '@remotion/zod-types';

// zColor() renders as a color picker in the Remotion Studio sidebar.
export const stingerSchema = z.object({
  direction: z.enum(['left', 'right', 'up', 'down']),
  // At least one color: an empty array would render a silent fully-transparent clip.
  panelColors: z.array(zColor()).min(1),
  // .int() so Studio shows whole-frame sliders (fractional frames are meaningless).
  stagger: z.number().int().min(0).max(30),
  holdFrames: z.number().int().min(0).max(40),
  title: z.string(),
});
