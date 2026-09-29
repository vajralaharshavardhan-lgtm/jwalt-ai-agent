import React from 'react';
import {AbsoluteFill} from 'remotion';
import {Particles} from '../components/Atmosphere';
import {LogoReveal} from '../components/LogoReveal';
import {Seed} from '../components/Seed';
import {copy} from '../content/copy';
import {ease, lerp, progress, tween} from '../utils/easing';
import {useLayout} from '../utils/layout';
import {useSceneFrame} from '../utils/scene';
import {RETURN_SEED_END} from './ReturnToSeed';

/**
 * FINAL REVEAL · 0:40–0:45
 * The floating seed recedes and condenses into a single point of warm light.
 * The light opens into a golden hairline; the wordmark rises out of it, the
 * brand line descends from it. Hold ~2 s, then fade to black.
 */
export const FinalReveal: React.FC = () => {
  const f = useSceneFrame();
  const {portrait, u, width, height} = useLayout();
  const cy = height * (portrait ? 0.44 : 0.5);

  // Seed recedes into a point of light (0 → ~24).
  const recede = progress(f, 0, 26, ease.in);
  const seedSize = lerp(RETURN_SEED_END.size, 40, recede) * u;
  const seedOpacity = 1 - progress(f, 14, 12, ease.inOut);
  const point = tween(f, [8, 20], [0, 1], ease.out) * (1 - progress(f, 30, 16, ease.inOut));
  const fadeOut = progress(f, 134, 16, ease.inOut);

  // Seed position: from the centre (where it floated) up to where the hairline sits.
  const lockupLineY = cy + (portrait ? -10 : -6) * u;
  const seedY = lerp(height * (portrait ? 0.44 : 0.5), lockupLineY, recede);

  return (
    <AbsoluteFill style={{background: '#020302'}}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse ${portrait ? '80% 40%' : '50% 60%'} at 50% ${(cy / height) * 100}%, rgba(40,30,16,0.55) 0%, rgba(12,10,6,0.3) 45%, rgba(0,0,0,0) 80%)`,
          opacity: tween(f, [10, 60], [0.3, 1]),
        }}
      />
      <Particles seed="fr-dust" count={22} size={[2, 7]} drift={{x: 2, y: -4}} opacity={0.3} focus={0.5} color="246,214,160" />

      {seedOpacity > 0 ? (
        <div
          style={{
            position: 'absolute',
            left: width / 2,
            top: seedY,
            transform: `translate(-50%, -50%) rotate(${RETURN_SEED_END.rotate}deg)`,
            opacity: seedOpacity,
          }}
        >
          <Seed id="s9-seed" size={seedSize} lightX={0.38} lightY={0.28} keyLight={lerp(0.85, 0.3, recede)} rimLight={0.95} glow={recede} crack={0} />
        </div>
      ) : null}

      {/* Point of light the lockup is born from */}
      <div
        style={{
          position: 'absolute',
          left: width / 2 - 70 * u,
          top: lockupLineY - 70 * u,
          width: 140 * u,
          height: 140 * u,
          borderRadius: '50%',
          opacity: point,
          background: 'radial-gradient(circle, rgba(255,250,235,1) 0%, rgba(246,196,124,0.6) 18%, rgba(246,196,124,0) 60%)',
          mixBlendMode: 'screen',
        }}
      />

      {/* Lockup: centred so the hairline sits where the light was */}
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', paddingTop: (portrait ? -80 : 0) * u}}>
        <div style={{transform: `translateY(${(portrait ? 12 : 30) * u}px)`}}>
          <LogoReveal
            frame={f}
            start={18}
            wordmark={copy.finalReveal.wordmark}
            tagline={copy.finalReveal.tagline}
            location={copy.finalReveal.location}
            u={u}
            portrait={portrait}
          />
        </div>
      </AbsoluteFill>

      <AbsoluteFill style={{background: '#000', opacity: fadeOut}} />
    </AbsoluteFill>
  );
};
