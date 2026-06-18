import {describe, it, expect} from 'vitest';
import {chaseStingerSchema} from './schema';
import {DEFAULT_ROBOTS} from './constants';

describe('chaseStingerSchema', () => {
  it('parses props with the default robots', () => {
    const parsed = chaseStingerSchema.parse({
      direction: 'right',
      panelColors: ['#0e0e12', '#7c3aed'],
      stagger: 4,
      holdFrames: 10,
      robots: DEFAULT_ROBOTS,
      trail: 8,
      scouts: 2,
      wipeDelay: 10,
    });
    expect(parsed.robots.length).toBe(6);
    expect(parsed.robots[0].idDots).toHaveLength(4);
  });

  it('rejects a robot whose idDots is not a 4-tuple', () => {
    expect(() =>
      chaseStingerSchema.parse({
        direction: 'right',
        panelColors: ['#000000'],
        stagger: 4,
        holdFrames: 10,
        robots: [{teamColor: '#1e64ff', idDots: ['#00d000', '#ff20c0']}],
        trail: 8,
        scouts: 2,
        wipeDelay: 10,
      }),
    ).toThrow();
  });

  it('does not carry a title field (omitted from the base schema)', () => {
    expect('title' in chaseStingerSchema.shape).toBe(false);
  });
});
