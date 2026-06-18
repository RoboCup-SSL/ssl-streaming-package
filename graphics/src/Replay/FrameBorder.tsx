import React from 'react';

// The replay frame: top and bottom bars each split into `segmentColors.length`
// equal-width colour segments (left -> right), plus full-height left/right edge
// bars in the first/last colour. The centre stays transparent. `barThickness[i]`
// is the height of segment i's top & bottom pieces; `leftThickness`/`rightThickness`
// are the widths of the edge bars. The stinger animates these (top+bottom meet to
// cover the screen); the overlay passes uniform values for a static frame.
export const FrameBorder: React.FC<{
  segmentColors: string[]; // left -> right
  barThickness: number[]; // per-segment top/bottom bar height (px)
  leftThickness: number; // width of the full-height left edge bar
  rightThickness: number; // width of the full-height right edge bar
}> = ({segmentColors, barThickness, leftThickness, rightThickness}) => {
  const n = segmentColors.length;
  return (
    <>
      {leftThickness > 0 ? (
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: 0,
            bottom: 0,
            width: leftThickness,
            background: segmentColors[0],
          }}
        />
      ) : null}
      {rightThickness > 0 ? (
        <div
          style={{
            position: 'absolute',
            right: 0,
            top: 0,
            bottom: 0,
            width: rightThickness,
            background: segmentColors[n - 1],
          }}
        />
      ) : null}
      {segmentColors.map((color, i) => {
        const h = barThickness[i];
        if (h <= 0) {
          return null;
        }
        const left = `${(i * 100) / n}%`;
        const width = `${100 / n}%`;
        return (
          <React.Fragment key={i}>
            <div style={{position: 'absolute', left, width, top: 0, height: h, background: color}} />
            <div style={{position: 'absolute', left, width, bottom: 0, height: h, background: color}} />
          </React.Fragment>
        );
      })}
    </>
  );
};
