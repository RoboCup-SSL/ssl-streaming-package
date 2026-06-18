import os from 'os';
import {Config} from '@remotion/cli/config';

// PNG image format is required to carry an alpha channel through the
// frame pipeline. VP9 + no opaque background + yuva420p = real transparency.
Config.setVideoImageFormat('png');
Config.setCodec('vp9');
Config.setPixelFormat('yuva420p');

// --- Speed ---
// GPU-accelerate the Chromium rendering/rasterization stage (RTX 3070 via ANGLE),
// and render as many frames in parallel as we have cores (minus a couple for the OS
// + the ffmpeg encoder). Applies to every `render`/`still` and to Studio.
// NOTE: this speeds RENDERING, not encoding. VP9 (the transparent stingers' codec) is
// a CPU-only encoder and there is no GPU path for alpha video; the opaque `Standby`
// sidesteps that by encoding H.264 instead (see its render:standby script).
Config.setChromiumOpenGlRenderer('angle');
Config.setConcurrency(Math.max(1, os.cpus().length - 2));
