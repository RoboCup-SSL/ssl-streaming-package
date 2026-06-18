# SSL Streaming Package

An out-of-the-box streaming setup for the [RoboCup Small Size League](https://ssl.robocup.org/).
The RoboCup Small Size League (SSL) is an autonomous robot soccer competition where teams
of miniature robots (each fitting within an 18 cm diameter circle) play fast-paced,
11-vs-11 or 6-vs-6 matches.

The goal of this package is to make SSL livestreams **professional by default** — so that a
volunteer operator at any event (international, regional, or a spontaneous match anywhere in
the world), who knows Linux and programming but not OBS or video production, can produce a
clean, watchable, shareable stream with minimal setup and little room to get things wrong.

## Status & roadmap

Early scaffolding. The project ships in incremental MVPs, each delivering standalone value.
See [`docs/mvp-direction.md`](docs/mvp-direction.md) for the full rationale.

| Milestone | Theme | Scope |
|---|---|---|
| **MVP1** | *Looks pro, manual* | Pre-built OBS template (1.1, 1.2, 1.3, 1.5) + Game-Controller text push (2.2) + Python controller skeleton (2.0) + operator handbook. Operator drives streams/scenes/commentary manually inside a polished template. |
| **MVP2** | *Runs itself* | Per-match auto streaming (2.1, first in line) + automatic scene switching (2.3). Unattended fallback when no operator is available. |
| **Later** | *Enhancements* | Digital ball-zoom (2.4), commentator replay (1.4), AR overlays + calibration (3.x), MediaMTX manager (4.x), Windows support. |

**Operating model:** thin-first. The professional look lives in a shared OBS template. By
default the operator does everything manually (with a beginner handbook); the Python
controller starts as a live-data feeder and grows into a full unattended mode.

---

## Field infrastructure — Hardware

At the RoboCup, all the matches will be streamed. Each soccer field will have multiple
cameras around it, and one streaming pc. The cameras are all somehow connected to this
streaming pc (via ethernet rtsp, hdmi capture cards, spi capture cards, etc). The streaming
PC will run an OBS instance, which will take all these cameras, use them to create multiple
scenes, and it will livestream to youtube. The streaming PC will also have a microphone for
a commentator, as well as a commentator-facing webcam.

## Field infrastructure — Software

A second computer, owned and controlled by the league committee, will run the small size
league software. This includes:

- **The game controller.** The game controller is responsible from deciding and announcing
  the current state of the game. This includes match phase such as first half, half time,
  second half, penalty shootout, match over, etc. It also includes match state such as free
  kick, penalty, normal play, yellow card, foul, etc.

- **The AutoRef.** The autoref does many things, but only relevant now is that it broadcasts
  the location of the 12 (divb) or 22 (diva) robots + the ball on the soccer field.

- **Vision software** (either legacy SSL-Vision, or the newer Vision-Processor). The vision
  software is responsible for using multiple field overhead cameras to find where the robots
  + ball are, and send this raw data to the autoref. The autoref then uses filters to create
  a coherent world view, which it then broadcasts. Additionally, the vision software
  broadcasts the geometry of the field such as width, height, line thickness, etc.

The three software packages mentioned above all communicate via protobuf.

The livestream will ideally support multiple features.

## 1. OBS basics

- **1.1.** When switching cameras, the scenes should fade into eachother.
- **1.2.** The commentator-facing webcam feed should be embedded / overlayed on top of the
  field-facing camera feeds, so that viewers will see mainly the field, and the commentators
  on the side of the video ("field-with-commentator feed").
- **1.3.** When switching from field-with-commentator feed to "commentator feed" (meaning
  fullscreen commentator, no field), or vice versa, OBS should play a custom stinger.
- **1.4.** The commentator should be able to replay the last few seconds of his feed, where
  only the video is replayed, but the audio is not. This will allow the commentator to replay
  for example goals, fouls, while commentating on these. A second custom stinger should be
  played when going into the "replay feed".
- **1.5.** All the feeds should support custom banners / logo overlays.

## 2. Autonomous OBS control

**Preface:** A python script will control OBS via the websocket interface. This python
script will run next to OBS localhost on the same machine. It's able to listen to all the
protobuf messages from the game controller, autoref, and vision software mentioned above.
Additionally, it will have a file with the schedule.

- **2.1.** It might occur that there are no commentators available to start or stop the
  livestreams. The python script should be able to automatically start and stop the
  livestream based on the schedule + time of day and the messages from the Game Controller
  (such as NORMAL_FIRST_HALF_PRE and POST_GAME and team names). Every match will have its own
  livestream url, meaning a different YouTube key. Python should also be able to handle this.
  The matches will be manually pre-scheduled on YouTube.
- **2.2.** The python script should be able to push text (such as team names / scores / next
  up matches) towards OBS, so that OBS can render this text dynamically.
- **2.3.** The python script should be able to switch to scenes / banners automatically (live
  match, half time, post match with score etc. Scenes + banners are to be determined).
- **2.4.** The python script should be able to zoom in a camera feed on the location of the
  ball. This is a simply digital zoom. In no way is the actual camera controlled, only its
  feed is transformed within OBS.

## 3. Dynamic overlays / Augmented reality

**Preface:** The robots are small and the ball is even smaller. The robots move fast and all
look alike. This makes it difficult for spectators to see what's going on. video feed
overlays could provide a solution. Clear colors could be rendered under / around the robots,
and the location of the ball could be indicated with a big circle around it. This does come
with some challenges:

- **Challenge 1:** Each camera has to be calibrated towards the field. A transformation
  matrix will need to be determined to map field x-y coordinates to pixels.
- **Challenge 2:** The overlay rendering has to be fast. Ideally, given a 30fps, the
  rendering shouldn't take more that 1/30s of a second.

- **3.1.** The overlay should be sent as a separate stream to OBS, using an alpha background.
  This allows OBS to optionally render it on top of the corresponding camera feed.
- **3.2.** The overlay should be able to indicate the position of the ball.
- **3.3.** The overlay should be able to indicate the team to which robots belong (either
  yellow or blue).
- **3.4.** A "calibration program" should allow the users to open a webcam stream, and click
  on certain points in the field. Using these points, a calibration matrix is generated.
- **3.5.** An "overlay program" should be able to open both a video feed and a corresponding
  calibration matrix, and push out an overlay video feed with an alpha background.

## 4. MediaMTX manager

**Preface:** Multiple programs have been detected which need access to the video feeds. OBS,
"calibration program", "overlay program". To faciliate this access, a MediaMTX instance will
be placed in the middle of it all. It will be the hub through which all video streams +
overlay streams flow. Webcam / camera streams will be registered at MediaMTX, which will be
pulled by the aforementioned programs. The "overlay program" will also push its overlay
towards MediaMTX, which will be pulled by OBS. MediaMTX however doesn't seem to have a
convenient interface, or even an command line interface.

- **4.1.** Users can register video feeds within MediaMTX, meaning ip address / usb port +
  endpoint.
- **4.2.** Users can remove video feeds within MediaMTX, given an endpoint.

## 5. Package deployment

**Preface:** This is a meta feature regarding the management of this entire project. What I
want is a single monorepo containing all of these separate projects. Each project should
stand on its own, meaning all communication between programs will go via TCP / UDP /
WebSockets etc. The entire project should be able to be bundled up easily for deployment on a
computer. The project will target ubuntu 24+ computers, but windows compability would be a
nice to have (but not required).
