import React, {useMemo} from 'react';
import {AbsoluteFill} from 'remotion';
import {AnimatedText} from '../components/AnimatedText';
import {Bokeh, LightLeak, Particles} from '../components/Atmosphere';
import {CinematicImage} from '../components/CinematicImage';
import {ImageReveal} from '../components/ImageReveal';
import {getSlot} from '../assets/useSlot';
import {copy} from '../content/copy';
import {palette} from '../styles/brand';
import {ease, lerp, progress, tween} from '../utils/easing';
import {type Pt, lerpPts, pt, resample, rotate, smoothPath} from '../utils/geometry';
import {useLayout} from '../utils/layout';
import {useSceneFrame} from '../utils/scene';
import {leafGeometry} from '../visuals/leaf';
import {Field, fieldSetup, rowLine} from '../visuals/field';

/**
 * SCENE 04 · 0:13–0:18
 * The line-art leaf becomes living tissue, backlit by a low sun. The camera
 * pushes through it; its veins swing into perspective as the furrows of a
 * field, which opens out at golden hour and dollies toward us.
 */
export const FieldValidation: React.FC = () => {
  const f = useSceneFrame();
  const {portrait, u, width, height, marginX, headlineSize, supportSize, safeBottom} = useLayout();
  const photo = getSlot('field-wide');

  // --- Leaf camera ---------------------------------------------------------
  const leafL = (portrait ? 1500 : 1150) * u;
  const leaf = useMemo(() => leafGeometry(leafL, leafL * 0.36, 0.1, 6), [leafL]);
  const center = leaf.mid(0.5);
  const turn = progress(f, -16, 50, ease.inOut);
  const rot = lerp(0.56, portrait ? 0 : -0.04, turn);
  const leafScale = lerp(1, 1.5, progress(f, -16, 50, ease.gentle)) * lerp(1, 2.6, progress(f, 30, 40, ease.in));
  const toScreen = (p: Pt) => {
    const r = rotate(pt((p.x - center.x) * leafScale, (p.y - center.y) * leafScale), rot);
    return pt(width / 2 + r.x, height * (portrait ? 0.5 : 0.52) + r.y);
  };

  const tissue = tween(f, [-16, 6], [0, 1], ease.inOut) * (1 - progress(f, 36, 22, ease.inOut));
  const leafIn = tween(f, [-16, -4], [0, 1], ease.out);
  const morph = progress(f, 34, 36, ease.inOut);
  const lineGlow = tween(f, [30, 46], [0.55, 1], ease.inOut) * (1 - progress(f, 66, 26, ease.inOut));
  const fieldIn = progress(f, 48, 26, ease.inOut);
  const plantsIn = progress(f, 58, 32, ease.out);

  // --- Vein → furrow morph -------------------------------------------------
  const setup = fieldSetup(width, height, u, portrait);
  const N = 16;
  const midRow = (setup.rows - 1) / 2;
  const sources: Pt[][] = [];
  const targets: Pt[][] = [];
  // Midrib → centre row (base at bottom, tip at the vanishing point).
  sources.push(resample(leaf.midrib.map(toScreen), N));
  targets.push(rowLine(setup, midRow, N));
  // Vein pair i: outer end → bottom of row. Veins near the base → outer rows.
  leaf.veins.forEach((v, idx) => {
    const pair = Math.floor(idx / 2);
    const side = idx % 2 === 0 ? 1 : -1;
    const row = midRow + side * (midRow - pair);
    sources.push(resample([...v].reverse().map(toScreen), N));
    targets.push(rowLine(setup, row, N));
  });
  const lines = sources.map((s, i) => lerpPts(s, targets[i], morph));

  const outline = leaf.outline.map(toScreen);
  const leafD = smoothPath(outline, true);
  const time = Math.max(0, (f - 40) / 30);

  return (
    <AbsoluteFill style={{background: '#05100A'}}>
      {/* Sun behind the leaf: warm bokeh */}
      <AbsoluteFill style={{opacity: leafIn * (1 - fieldIn)}}>
        <AbsoluteFill style={{background: 'radial-gradient(ellipse 70% 70% at 62% 38%, #6B7A3A 0%, #24381C 45%, #07120A 100%)'}} />
        <Bokeh seed="f-bokeh" count={16} colors={['246,210,140', '200,220,140']} radius={[40, 140]} opacity={0.4} shiftX={-f * 1.2 * u} />
      </AbsoluteFill>

      {/* The field (fades in under the lines) */}
      <AbsoluteFill style={{opacity: fieldIn}}>
        <Field setup={setup} time={time} plantsIn={plantsIn} furrows={1} />
      </AbsoluteFill>
      {photo ? (
        <ImageReveal progress={progress(f, 78, 30, ease.inOut)} type="focus">
          <CinematicImage src={photo.src} kind={photo.kind === 'video' ? 'video' : 'image'} frame={f - 78} duration={90} grade="warm" scaleFrom={1.08} scaleTo={1.02} />
        </ImageReveal>
      ) : null}

      <svg width={width} height={height} style={{position: 'absolute', inset: 0}}>
        <defs>
          <radialGradient id="fv-tissue" cx="0.55" cy="0.4" r="0.75">
            <stop offset="0" stopColor="#D5E98A" />
            <stop offset="0.35" stopColor="#8EBB4E" />
            <stop offset="0.75" stopColor="#3E7A2E" />
            <stop offset="1" stopColor="#173A16" />
          </radialGradient>
          <filter id="fv-cells" x="0" y="0" width="100%" height="100%">
            <feTurbulence type="fractalNoise" baseFrequency={0.09 / Math.max(0.5, leafScale * u)} numOctaves={2} seed={5} />
            <feColorMatrix type="matrix" values="0 0 0 0 0.1  0 0 0 0 0.2  0 0 0 0 0.05  0 0 0 1.4 -0.45" />
          </filter>
          <clipPath id="fv-leaf-clip">
            <path d={leafD} />
          </clipPath>
          <filter id="fv-glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation={6 * u} />
          </filter>
        </defs>

        {/* Backlit tissue */}
        <g opacity={tissue * leafIn}>
          <path d={leafD} fill="url(#fv-tissue)" />
          <g clipPath="url(#fv-leaf-clip)">
            <rect width={width} height={height} filter="url(#fv-cells)" opacity={0.28} style={{mixBlendMode: 'multiply'}} />
          </g>
          <path d={leafD} fill="none" stroke="#10260E" strokeOpacity={0.7} strokeWidth={5 * u} />
        </g>
        {/* Line-art edge carried over from Research, fading as tissue appears */}
        <path d={leafD} fill="none" stroke={palette.cream} strokeOpacity={0.9 * leafIn * (1 - tissue) * (1 - morph)} strokeWidth={1.6} />

        {/* Veins → furrows */}
        {lines.map((l, i) => {
          const d = smoothPath(l);
          const w = (i === 0 ? 7 : 3.2) * u * lerp(1, 0.6, morph);
          return (
            <g key={i} opacity={lineGlow * leafIn}>
              <path d={d} fill="none" stroke="#F1F7C4" strokeOpacity={0.35} strokeWidth={w * 3.5} filter="url(#fv-glow)" />
              <path d={d} fill="none" stroke={i === 0 ? '#F3F6D2' : '#E4F0B0'} strokeOpacity={0.9} strokeWidth={w} strokeLinecap="round" />
            </g>
          );
        })}
      </svg>

      <LightLeak opacity={0.35 * tween(f, [40, 60], [0, 1]) * (1 - progress(f, 70, 40))} x={0.6} y={0.38} />
      <Particles seed="f-pollen" count={30} size={[2, 9]} drift={{x: -14, y: -4}} opacity={0.5 * fieldIn} focus={0.3} color="255,226,170" />

      {/* Scrim for legibility */}
      <AbsoluteFill
        style={{
          background: portrait
            ? 'linear-gradient(to top, rgba(8,10,6,0.72) 0%, rgba(8,10,6,0.3) 30%, rgba(0,0,0,0) 50%)'
            : 'linear-gradient(to top, rgba(8,10,6,0.66) 0%, rgba(8,10,6,0.2) 32%, rgba(0,0,0,0) 48%)',
        }}
      />
      <AbsoluteFill
        style={{
          justifyContent: 'flex-end',
          alignItems: portrait ? 'center' : 'flex-start',
          paddingLeft: marginX,
          paddingRight: marginX,
          paddingBottom: portrait ? safeBottom : safeBottom,
        }}
      >
        <AnimatedText
          text={copy.field.headline}
          start={10}
          exit={136}
          size={headlineSize}
          align={portrait ? 'center' : 'left'}
          maxWidth={portrait ? width - marginX * 2 : 1100 * u}
          style={{textShadow: '0 2px 30px rgba(0,0,0,0.55)'}}
        />
        <AnimatedText
          text={copy.field.support}
          start={70}
          exit={136}
          variant="support"
          mode="fade"
          size={supportSize}
          align={portrait ? 'center' : 'left'}
          style={{marginTop: 18 * u, textShadow: '0 1px 18px rgba(0,0,0,0.6)'}}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
