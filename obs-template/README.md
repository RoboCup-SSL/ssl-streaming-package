# obs-template

The **pre-built OBS scene collection** operators import and barely touch — the heart of MVP1's
"professional by default" look. Ships the scenes, transitions, overlays, and the assets they
reference, so a volunteer with no OBS knowledge inherits a clean broadcast.

Planned contents:
- OBS **scene-collection export** (`.json`) — scenes for field-only, field+commentator,
  commentator-fullscreen, halftime, pre/post-match.
- **Transitions** wired to the stinger WebMs rendered by [`../graphics`](../graphics/) (1.3).
- **Overlay** layers: brand frames/banners (1.5), the commentator-cam layout (1.2), scene
  fades (1.1).
- A `obs-urlsource` text source pulling live match text from [`../services/obs-live-data`](../services/obs-live-data/) (2.2).
- Setup notes / per-PC import checklist.

See the operator-facing instructions in [`../docs/handbook`](../docs/handbook/).

## Status

**Not built yet.** Scaffold only. The graphics it references already exist in `../graphics`.
