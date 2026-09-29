// Remotion CLI configuration. Applies to `remotion studio` and `remotion render`.
// See https://www.remotion.dev/docs/config
import {Config} from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setJpegQuality(95);
Config.setCodec('h264');
// CRF 16 = visually lossless for grain-heavy footage. Raise (e.g. 22) for smaller files.
Config.setCrf(16);
Config.setPixelFormat('yuv420p');
Config.setOverwriteOutput(true);
Config.setEntryPoint('src/index.ts');

// Optional: point Remotion at an existing Chrome/Chromium instead of letting it
// download its own headless shell (useful on locked-down networks).
if (process.env.REMOTION_BROWSER_EXECUTABLE) {
  Config.setBrowserExecutable(process.env.REMOTION_BROWSER_EXECUTABLE);
}
