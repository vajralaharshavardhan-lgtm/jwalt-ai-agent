import React from 'react';
import {Composition, Folder} from 'remotion';
import {PremiumSeedsFilm, SCENE_COMPONENTS} from './compositions/PremiumSeedsFilm';
import {AssetGuide} from './compositions/AssetGuide';
import {FilmGrain, Vignette} from './components/Atmosphere';
import {FPS, SCENES, SCENE_ORDER, TOTAL_FRAMES} from './utils/timeline';
import {StandaloneScene} from './utils/scene';
import {loadBrandFonts} from './styles/fonts';

loadBrandFonts();

const ScenePreview: React.FC<{id: keyof typeof SCENES}> = ({id}) => {
  const Scene = SCENE_COMPONENTS[id];
  return (
    <StandaloneScene id={id}>
      <Scene />
      <Vignette strength={0.55} />
      <FilmGrain />
    </StandaloneScene>
  );
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* Master film, 16:9: YouTube, LinkedIn, website hero, presentations. */}
      <Composition
        id="PremiumSeedsFilm"
        component={PremiumSeedsFilm}
        durationInFrames={TOTAL_FRAMES}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{withAudio: true, grain: 0.085}}
      />
      {/* 9:16: Instagram Reels, YouTube Shorts, Stories. */}
      <Composition
        id="PremiumSeedsFilmVertical"
        component={PremiumSeedsFilm}
        durationInFrames={TOTAL_FRAMES}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{withAudio: true, grain: 0.085}}
      />
      {/* 4:5: Instagram / LinkedIn feed. */}
      <Composition
        id="PremiumSeedsFilmFeed"
        component={PremiumSeedsFilm}
        durationInFrames={TOTAL_FRAMES}
        fps={FPS}
        width={1080}
        height={1350}
        defaultProps={{withAudio: true, grain: 0.085}}
      />
      {/* Same film with labels showing where each drop-in asset appears. */}
      <Composition id="AssetGuide" component={AssetGuide} durationInFrames={TOTAL_FRAMES} fps={FPS} width={1920} height={1080} />
      <Folder name="Scenes">
        {SCENE_ORDER.map((id, i) => (
          <Composition
            key={id}
            id={`Scene${String(i + 1).padStart(2, '0')}-${id}`}
            component={ScenePreview}
            durationInFrames={SCENES[id].duration + SCENES[id].pre}
            fps={FPS}
            width={1920}
            height={1080}
            defaultProps={{id}}
          />
        ))}
      </Folder>
    </>
  );
};
