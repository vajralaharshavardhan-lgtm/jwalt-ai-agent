import React from 'react';
import {AbsoluteFill} from 'remotion';
import {AnimatedText} from '../components/AnimatedText';
import {Bokeh, Particles} from '../components/Atmosphere';
import {CinematicImage} from '../components/CinematicImage';
import {CropMorph} from '../components/CropMorph';
import {getSlot, type SlotId} from '../assets/useSlot';
import {copy} from '../content/copy';
import {palette} from '../styles/brand';
import {textStyles} from '../styles/typography';
import {ease, lerp, progress, tween} from '../utils/easing';
import {useLayout} from '../utils/layout';
import {useSceneFrame} from '../utils/scene';
import {CROPS} from '../visuals/crops';

// Montage timing (scene-local frames).
const FIRST = 6;
const FIRST_HOLD = 24;
const SLOT = 18;
const MORPH = 8;
/** Frame at which crop i is fully settled. */
const settleAt = (i: number) => (i === 0 ? FIRST + 16 : FIRST + FIRST_HOLD + (i - 1) * SLOT + MORPH);

const montageState = (f: number) => {
  for (let i = CROPS.length - 1; i >= 1; i--) {
    const end = settleAt(i);
    const start = end - MORPH;
    if (f >= start) {
      return {a: i - 1, b: i, t: f >= end ? 1 : progress(f, start, MORPH, ease.inOut)};
    }
  }
  return {a: 0, b: 0, t: 0};
};

/**
 * SCENE 05 · 0:18–0:24
 * Specimen-style montage: eight crops presented one after another, each
 * morphing point-for-point into the next (shape, colour, orientation),
 * with "25+ vegetable crops" set large beside them.
 */
export const CropPortfolio: React.FC = () => {
  const f = useSceneFrame();
  const {portrait, u, width, height, marginX, headlineSize, supportSize, capsSize, safeBottom} = useLayout();
  const {a, b, t} = montageState(f);
  const current = t < 0.5 ? a : b;
  const draw = progress(f, FIRST, 20, ease.out);
  const bgIn = tween(f, [-14, 0], [0, 1], ease.inOut);
  const out = progress(f, 158, 22, ease.in);

  const cropX = portrait ? width * 0.5 : width * 0.665;
  const cropY = portrait ? height * 0.37 : height * 0.47;
  const cropSize = (portrait ? 880 : 780) * u * lerp(1, 1.08, progress(f, 0, 180, ease.gentle));
  const labelY = portrait ? height * 0.6 : height - 120 * u;

  // Photo mode: only when every crop slot has a real photo, so the montage stays consistent.
  const photos = CROPS.map((c) => getSlot(c.slot as SlotId));
  const photoMode = photos.every(Boolean);
  const labelDip = 1 - Math.sin(Math.PI * t) * (a !== b ? 1 : 0);

  const [num, ...rest] = copy.crops.headline.split(' ');
  const hasNumber = /^\d/.test(num);

  return (
    <AbsoluteFill>
      <AbsoluteFill
        style={{
          opacity: bgIn,
          background: `radial-gradient(ellipse ${portrait ? '90% 50%' : '55% 80%'} at ${(cropX / width) * 100}% ${(cropY / height) * 100}%, #17402C 0%, #0C2519 45%, #040D08 100%)`,
        }}
      />
      <AbsoluteFill style={{opacity: bgIn}}>
        <Bokeh seed="c-bokeh" count={10} colors={['165,204,124', '201,165,107']} radius={[30, 90]} opacity={0.18} shiftX={-f * 0.6 * u} />
        <Particles seed="c-dust" count={20} size={[2, 6]} drift={{x: 3, y: -5}} opacity={0.3} />
      </AbsoluteFill>

      {/* Specimen ring */}
      <svg width={width} height={height} style={{position: 'absolute', inset: 0, opacity: bgIn * (1 - out)}}>
        <circle
          cx={cropX}
          cy={cropY}
          r={cropSize * 0.56}
          fill="none"
          stroke={palette.husk}
          strokeOpacity={0.28}
          strokeWidth={1.2}
          pathLength={1}
          strokeDasharray="1 1"
          strokeDashoffset={1 - progress(f, 2, 40, ease.out)}
          transform={`rotate(-90 ${cropX} ${cropY})`}
        />
        <circle cx={cropX} cy={cropY} r={cropSize * 0.6} fill="none" stroke={palette.cream} strokeOpacity={0.06} strokeWidth={1} />
        {!photoMode ? (
          <CropMorph id="cm" from={CROPS[a]} to={CROPS[b]} t={t} x={cropX} y={cropY} size={cropSize} draw={draw} opacity={1 - out} />
        ) : null}
      </svg>

      {photoMode
        ? photos.map((p, i) => {
            const vis = i === a ? 1 - t : i === b ? t : 0;
            if (!p || vis <= 0) {
              return null;
            }
            const r = cropSize * 0.5;
            return (
              <div
                key={i}
                style={{
                  position: 'absolute',
                  left: cropX - r,
                  top: cropY - r,
                  width: r * 2,
                  height: r * 2,
                  borderRadius: '50%',
                  overflow: 'hidden',
                  opacity: vis * (1 - out),
                }}
              >
                <CinematicImage src={p.src} frame={f - settleAt(i)} duration={30} vignette={0.3} />
              </div>
            );
          })
        : null}

      {/* Crop name */}
      <div
        style={{
          position: 'absolute',
          left: cropX - 400 * u,
          width: 800 * u,
          top: labelY,
          textAlign: 'center',
          opacity: draw * labelDip * (1 - out),
          filter: `blur(${(1 - labelDip) * 6}px)`,
        }}
      >
        <span style={{...textStyles.caps, fontSize: capsSize * 1.15, color: palette.huskLight}}>{copy.crops.names[current] ?? CROPS[current].name}</span>
      </div>

      {/* Headline block */}
      <AbsoluteFill
        style={{
          justifyContent: portrait ? 'flex-end' : 'center',
          alignItems: portrait ? 'center' : 'flex-start',
          paddingLeft: marginX,
          paddingRight: marginX,
          paddingBottom: portrait ? safeBottom : 0,
        }}
      >
        <div style={{display: 'flex', flexDirection: 'column', alignItems: portrait ? 'center' : 'flex-start'}}>
          {hasNumber ? (
            <AnimatedText
              text={num}
              start={8}
              exit={156}
              size={headlineSize * (portrait ? 2.6 : 3)}
              mode="fade"
              style={{lineHeight: 0.9, color: palette.huskLight, fontVariationSettings: '"opsz" 144, "SOFT" 20, "WONK" 0', fontWeight: 250}}
            />
          ) : null}
          <AnimatedText
            text={hasNumber ? rest.join(' ') : copy.crops.headline}
            start={16}
            exit={156}
            size={headlineSize}
            align={portrait ? 'center' : 'left'}
            style={{marginTop: 8 * u}}
          />
          <AnimatedText
            text={copy.crops.support}
            start={92}
            exit={156}
            variant="support"
            mode="fade"
            size={supportSize}
            align={portrait ? 'center' : 'left'}
            style={{marginTop: 26 * u}}
          />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
