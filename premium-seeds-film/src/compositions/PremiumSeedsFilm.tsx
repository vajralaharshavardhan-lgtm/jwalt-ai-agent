import React from 'react';
import {AbsoluteFill} from 'remotion';
import {FilmGrain, Vignette} from '../components/Atmosphere';
import {Soundtrack} from '../components/Soundtrack';
import {OpeningSeed} from '../scenes/OpeningSeed';
import {Germination} from '../scenes/Germination';
import {Research} from '../scenes/Research';
import {FieldValidation} from '../scenes/FieldValidation';
import {CropPortfolio} from '../scenes/CropPortfolio';
import {TopGunF1} from '../scenes/TopGunF1';
import {FarmerHarvest} from '../scenes/FarmerHarvest';
import {ReturnToSeed} from '../scenes/ReturnToSeed';
import {FinalReveal} from '../scenes/FinalReveal';
import {ScenePlacement} from '../utils/scene';
import {loadBrandFonts} from '../styles/fonts';
import type {SceneId} from '../utils/timeline';

loadBrandFonts();

export const SCENE_COMPONENTS: Record<SceneId, React.FC> = {
  openingSeed: OpeningSeed,
  germination: Germination,
  research: Research,
  field: FieldValidation,
  crops: CropPortfolio,
  topGun: TopGunF1,
  harvest: FarmerHarvest,
  returnToSeed: ReturnToSeed,
  finalReveal: FinalReveal,
};

export type FilmProps = {
  /** Play the soundtrack (music + sound design). */
  withAudio?: boolean;
  /** Film grain strength (0 disables). */
  grain?: number;
};

/**
 * The full 45-second film. Orientation-agnostic: the same component is
 * registered at 1920×1080, 1080×1920 and 1080×1350 in Root.tsx.
 */
export const PremiumSeedsFilm: React.FC<FilmProps> = ({withAudio = true, grain = 0.085}) => {
  return (
    <AbsoluteFill style={{background: '#000'}}>
      <ScenePlacement id="openingSeed">
        <OpeningSeed />
      </ScenePlacement>
      <ScenePlacement id="germination">
        <Germination />
      </ScenePlacement>
      <ScenePlacement id="research">
        <Research />
      </ScenePlacement>
      <ScenePlacement id="field">
        <FieldValidation />
      </ScenePlacement>
      <ScenePlacement id="crops">
        <CropPortfolio />
      </ScenePlacement>
      <ScenePlacement id="topGun">
        <TopGunF1 />
      </ScenePlacement>
      <ScenePlacement id="harvest">
        <FarmerHarvest />
      </ScenePlacement>
      <ScenePlacement id="returnToSeed">
        <ReturnToSeed />
      </ScenePlacement>
      <ScenePlacement id="finalReveal">
        <FinalReveal />
      </ScenePlacement>
      <Vignette strength={0.55} />
      {grain > 0 ? <FilmGrain opacity={grain} /> : null}
      {withAudio ? <Soundtrack /> : null}
    </AbsoluteFill>
  );
};
