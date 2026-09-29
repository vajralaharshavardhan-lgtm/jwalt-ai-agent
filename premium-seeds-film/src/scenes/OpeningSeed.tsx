import React from 'react';
import {AbsoluteFill} from 'remotion';
import {AnimatedText} from '../components/AnimatedText';
import {Particles} from '../components/Atmosphere';
import {Seed} from '../components/Seed';
import {copy} from '../content/copy';
import {ease, lerp, progress, tween} from '../utils/easing';
import {useLayout} from '../utils/layout';
import {useSceneFrame} from '../utils/scene';

/** Seed pose at the last frame of this scene; Germination starts from it (match cut). */
export const OPENING_SEED_END = {scale: 1.1, rotate: -3, lightX: 0.42, lightY: 0.3};

export const seedBaseSize = (portrait: boolean, u: number) => (portrait ? 760 : 620) * u;
export const seedCenterY = (portrait: boolean, height: number) => height * (portrait ? 0.4 : 0.45);

/**
 * SCENE 01 · 0:00–0:04
 * Black. A single seed emerges from darkness: rim light first, then a slow
 * key light sweeps across it while the lens pulls focus and pushes in.
 * A hairline crack opens and leaks warm light (hand-off to Germination).
 */
export const OpeningSeed: React.FC = () => {
  const f = useSceneFrame();
  const {portrait, u, cx, height, width, headlineSize, safeBottom, marginX} = useLayout();

  const rim = tween(f, [4, 30], [0, 0.95], ease.out);
  const key = tween(f, [14, 70], [0, 1], ease.cinematic);
  const push = progress(f, 0, 120, ease.gentle);
  const scale = lerp(0.86, OPENING_SEED_END.scale, push);
  const rotate = lerp(-7, OPENING_SEED_END.rotate, push);
  const lightX = lerp(0.12, OPENING_SEED_END.lightX, progress(f, 0, 110, ease.gentle));
  const lightY = lerp(0.18, OPENING_SEED_END.lightY, progress(f, 0, 110, ease.gentle));
  const focusBlur = tween(f, [0, 36], [9, 0], ease.out) * u;
  const crack = progress(f, 86, 26, ease.inOut);
  const glow = progress(f, 94, 26, ease.in);
  const size = seedBaseSize(portrait, u);
  const sy = seedCenterY(portrait, height);
  const ambient = tween(f, [10, 90], [0, 1], ease.gentle);

  return (
    <AbsoluteFill style={{background: '#020403'}}>
      {/* Faint warm studio falloff behind the seed. */}
      <AbsoluteFill
        style={{
          opacity: ambient * 0.9,
          background: `radial-gradient(ellipse ${portrait ? '70% 40%' : '45% 60%'} at 50% ${(sy / height) * 100}%, rgba(92,66,34,0.35) 0%, rgba(30,22,12,0.18) 45%, rgba(0,0,0,0) 75%)`,
        }}
      />
      <Particles
        seed="s1-dust"
        count={portrait ? 26 : 34}
        size={[2, 10]}
        drift={{x: 4, y: -6}}
        opacity={0.35 * ambient}
        focus={0.45}
        maxBlur={8}
      />
      <div
        style={{
          position: 'absolute',
          left: cx,
          top: sy,
          transform: `translate(-50%, -50%) rotate(${rotate}deg) scale(${scale})`,
        }}
      >
        <Seed
          id="s1-seed"
          size={size}
          lightX={lightX}
          lightY={lightY}
          keyLight={key}
          rimLight={rim}
          crack={crack}
          glow={glow}
          blur={focusBlur}
        />
      </div>
      <AbsoluteFill
        style={{
          justifyContent: 'flex-end',
          alignItems: 'center',
          paddingBottom: portrait ? safeBottom + 40 * u : safeBottom * 0.9,
          paddingLeft: marginX,
          paddingRight: marginX,
        }}
      >
        <AnimatedText
          text={copy.openingSeed.headline}
          start={28}
          exit={90}
          size={headlineSize}
          align="center"
          maxWidth={portrait ? width - marginX * 2 : 1400 * u}
          style={{textShadow: '0 2px 30px rgba(0,0,0,0.6)'}}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
