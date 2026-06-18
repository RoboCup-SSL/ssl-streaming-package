import {describe, it, expect} from 'vitest';
import {stingerSchema} from './schema';

describe('stingerSchema', () => {
  it('parses well-formed props', () => {
    const parsed = stingerSchema.parse({
      direction: 'right',
      panelColors: ['#0e0e12', '#7c3aed'],
      stagger: 4,
      holdFrames: 10,
      title: '',
    });
    expect(parsed.panelColors).toHaveLength(2);
    expect(parsed.direction).toBe('right');
  });

  it('rejects an invalid direction', () => {
    expect(() =>
      stingerSchema.parse({
        direction: 'sideways',
        panelColors: ['#000000'],
        stagger: 4,
        holdFrames: 10,
        title: '',
      }),
    ).toThrow();
  });
});
