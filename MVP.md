# MVP Direction (JTBD)

_Validated 2026-06-18 — confirmed by reviewing past SSL YouTube streams (genuinely bad)._

## Two hirers

**Viewer** — wants to find / watch / replay *one specific match*. Today's streams are
8-hour blobs with multiple matches, not pre-scheduled, no per-match URLs. Job is
completely unmet.

**Operator** — volunteer, new every year, programmer/linux-literate but **not** an
OBS/AV expert. Pain is both a *skill gap* and a *motivation gap*, so the product must be
**good-by-default with zero effort**, not "tools to build good streams." Strong social
job: "don't be the embarrassing field."

## Operating model (DECIDED)

**Thin first.** The professional look/feel lives in a pre-built OBS template; the
operator does everything manually by default.

- **Default mode — "assisted manual":** operator starts/stops streams, talks, switches
  scenes, all inside the polished template so it looks pro regardless of skill. Ships
  with a beginner operator handbook.
- **Fallback mode — "unattended":** nobody available → launch OBS + the Python
  controller and walk away; it runs itself.

Both modes share the same OBS template. The Python controller starts life in MVP1 as a
GC-data feeder (scores/names) and grows automation in MVP2.

## Feature cut (DECIDED)

**MVP1 — "Looks pro, manual"**
- 1.1 scene fade transitions (OBS config)
- 1.2 commentator webcam overlay on field feed (scene layout)
- 1.3 stinger on field↔commentator switch (template asset + transition)
- 1.5 banners / logo overlays (template)
- 2.2 push text from Game Controller (team names / score / next-up)
- 2.0 Python controller skeleton (OBS websocket + protobuf listener) — foundation,
  starts as the 2.2 feeder
- Beginner operator handbook

**MVP2 — "Runs itself" (unattended fallback)**
- 2.1 auto start/stop per-match stream, per-match YouTube key, schedule + GC driven
  (*first in line — the headline*)
- 2.3 auto scene switching (live / halftime / post-match)
  - *Concrete seed (deferred, 2026-06-21):* trigger on the GC **Stage** (already decoded
    on every message). On a stage change call obs-websocket `SetCurrentProgramScene` to a
    scene named for that stage (e.g. `pregame` for `NORMAL_FIRST_HALF_PRE`, `1st_half`,
    `half_time`, …, `post_game`); switch only if such a scene exists, else no-op — same
    "name is the contract, missing = skip" rule as the overlay sources. Pairs with the Move
    transition plugin for animated phase changes. NOT in MVP1.

**Later**
- 2.4 digital ball-zoom
- 1.4 commentator replay (video-only, audio stripped) — part of a future *manual
  operator enhancements* set; replay buffer is easy, stripping audio is the tricky bit
- 3.1–3.5 AR overlays + calibration (high-risk: calibration + 30fps latency)
- 4.1–4.2 MediaMTX manager (only once overlays / multi-consumer exist)
- Windows support (nice-to-have)

## Deployment philosophy

Out-of-the-box, clone-and-run, Ubuntu 24+, hard to get wrong. Setup is a first-class
feature, grown incrementally (minimal in MVP1, expands with the controller in MVP2).
Distribution mechanism (bootstrap script vs other) not yet decided.
