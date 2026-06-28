import {z} from 'zod';
import {zColor} from '@remotion/zod-types';
import {robotSchema} from '../ChaseStinger/schema';

// The standalone robot composition reuses the chase robot's colours (teamColor +
// four ID dots) and adds presentation knobs that only matter when it's rendered on
// its own: body colour, on-canvas size, and which way the flat front points.
export const robotCompositionSchema = robotSchema.extend({
  bodyColor: zColor(),
  size: z.number().int().min(1), // rendered width/height of the robot, in px
  orientation: z.enum(['up', 'right']),
});

export type RobotCompositionProps = z.infer<typeof robotCompositionSchema>;
