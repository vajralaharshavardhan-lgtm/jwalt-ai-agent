import React from 'react';
import {Audio, interpolate} from 'remotion';
import {generatedAudio, getSlot} from '../assets/useSlot';
import {TOTAL_FRAMES} from '../utils/timeline';

/**
 * Mix levels. `music` is either public/assets/music.* (if present) or the
 * generated score; `sfx` is the generated sound-design layer, timed to the
 * picture. Set sfx to 0 to hear only a licensed track.
 */
export const AUDIO_MIX = {
  music: 0.9,
  sfx: 0.85,
  /** Fade (frames) applied to a drop-in music file so any track sits cleanly. */
  musicFadeIn: 20,
  musicFadeOut: 60,
};

export const Soundtrack: React.FC = () => {
  const licensed = getSlot('music');
  const score = generatedAudio('music');
  const sfx = generatedAudio('sfx');
  return (
    <>
      {licensed ? (
        <Audio
          src={licensed.src}
          volume={(f) =>
            AUDIO_MIX.music *
            interpolate(
              f,
              [0, AUDIO_MIX.musicFadeIn, TOTAL_FRAMES - AUDIO_MIX.musicFadeOut, TOTAL_FRAMES],
              [0, 1, 1, 0],
              {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
            )
          }
        />
      ) : score ? (
        <Audio src={score} volume={AUDIO_MIX.music} />
      ) : null}
      {sfx && AUDIO_MIX.sfx > 0 ? <Audio src={sfx} volume={AUDIO_MIX.sfx} /> : null}
    </>
  );
};
