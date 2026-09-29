import React from 'react';
import {AbsoluteFill, Img} from 'remotion';
import {AnimatedText} from '../components/AnimatedText';
import {Bokeh, LightLeak, Particles} from '../components/Atmosphere';
import {getSlot} from '../assets/useSlot';
import {copy} from '../content/copy';
import {palette} from '../styles/brand';
import {textStyles} from '../styles/typography';
import {ease, lerp, progress, tween} from '../utils/easing';
import {pt, rotate} from '../utils/geometry';
import {useLayout} from '../utils/layout';
import {useSceneFrame} from '../utils/scene';
import {MacroChilli} from '../visuals/MacroChilli';

/**
 * SCENE 06 · 0:24–0:29
 * Product reveal. A green chilli emerges from darkness in macro; a specular
 * band travels across it and the background parallaxes, reading as a slow
 * orbit. It ripens to deep red from the tip up (green fresh & red dry use).
 * Name first; the two figures only briefly and small.
 */
export const TopGunF1: React.FC = () => {
  const f = useSceneFrame();
  const {portrait, u, width, height, marginX, headlineSize, supportSize, capsSize, monoSize, safeBottom} = useLayout();
  const photo = getSlot('topgun-product');

  const bgIn = tween(f, [-14, 4], [0, 1], ease.inOut);
  const light = tween(f, [-6, 34], [0, 1], ease.cinematic);
  const orbit = progress(f, -14, 164, ease.gentle);
  const ripen = progress(f, 58, 52, ease.inOut);
  const out = progress(f, 132, 18, ease.in);

  // Chilli placement with a slow in-plane drift and push.
  const push = lerp(0.94, 1.06, orbit);
  const center = portrait ? pt(width * 0.5, height * 0.39) : pt(width * 0.69, height * 0.5);
  const half = (portrait ? 500 : 470) * u * push;
  const baseAngle = portrait ? 1.2 : 0.62;
  const angle = baseAngle + lerp(-0.05, 0.05, orbit);
  const a = rotate(pt(center.x - half, center.y), angle, center);
  const b = rotate(pt(center.x + half, center.y), angle, center);

  const specs = copy.topGun.specs;

  return (
    <AbsoluteFill>
      <AbsoluteFill
        style={{
          opacity: bgIn,
          background: `radial-gradient(ellipse ${portrait ? '90% 45%' : '60% 75%'} at ${(center.x / width) * 100}% ${(center.y / height) * 100}%, #10261A 0%, #07130C 50%, #020604 100%)`,
        }}
      />
      <AbsoluteFill style={{opacity: bgIn * (1 - out)}}>
        <Bokeh
          seed="tg-bokeh"
          count={8}
          colors={['120,170,90', '230,190,120', '90,140,80']}
          radius={[70, 190]}
          opacity={0.1 + 0.06 * ripen}
          shiftX={lerp(120, -160, orbit) * u}
        />
      </AbsoluteFill>
      <LightLeak opacity={0.22 * Math.sin(Math.PI * ripen)} x={0.75} y={0.3} color="255,150,110" />

      {photo ? (
        <AbsoluteFill style={{opacity: light * (1 - out), alignItems: 'center', justifyContent: 'center'}}>
          <Img
            src={photo.src}
            style={{
              position: 'absolute',
              left: center.x - half,
              top: center.y - half * 0.7,
              width: half * 2,
              height: half * 1.4,
              objectFit: 'contain',
              transform: `scale(${push}) rotate(${lerp(-2, 2, orbit)}deg)`,
              filter: 'drop-shadow(0 30px 60px rgba(0,0,0,0.6))',
            }}
          />
        </AbsoluteFill>
      ) : (
        <svg width={width} height={height} style={{position: 'absolute', inset: 0, opacity: 1 - out}}>
          <MacroChilli
            id="tg"
            a={a}
            b={b}
            bend={portrait ? -0.07 : 0.07}
            width={(portrait ? 64 : 58) * u * push}
            ripen={ripen}
            sheen={lerp(-0.62, 0.42, orbit)}
            light={light}
            squash={lerp(0.93, 1, Math.sin(orbit * Math.PI))}
          />
        </svg>
      )}
      <Particles seed="tg-dust" count={16} size={[2, 6]} drift={{x: -6, y: -3}} opacity={0.3 * bgIn} />

      {/* Copy */}
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
          <AnimatedText
            text={copy.topGun.eyebrow}
            start={10}
            exit={116}
            variant="caps"
            mode="fade"
            size={capsSize}
            style={{color: palette.husk}}
          />
          <AnimatedText
            text={copy.topGun.name}
            start={16}
            exit={118}
            mode="track"
            duration={40}
            size={headlineSize * 1.7}
            style={{marginTop: 18 * u, letterSpacing: '0.04em', lineHeight: 1, whiteSpace: 'nowrap'}}
          />
          <AnimatedText
            text={copy.topGun.descriptor}
            start={34}
            exit={118}
            variant="support"
            mode="fade"
            size={supportSize * 1.1}
            style={{marginTop: 18 * u, color: palette.cream}}
          />
          {/* The figures: brief, small, secondary */}
          <div style={{display: 'flex', gap: 34 * u, marginTop: 42 * u, alignItems: 'stretch'}}>
            {specs.map((s, i) => {
              const p = progress(f, 86 + i * 7, 20, ease.out);
              const o = p * (1 - progress(f, 112, 12, ease.in));
              return (
                <React.Fragment key={s.value}>
                  {i > 0 ? <div style={{width: 1, background: palette.husk, opacity: 0.5 * o}} /> : null}
                  <div style={{opacity: o, transform: `translateY(${(1 - p) * 10 * u}px)`, filter: `blur(${(1 - p) * 6}px)`}}>
                    <div style={{...textStyles.mono, fontSize: monoSize}}>{s.label}</div>
                    <div style={{...textStyles.headline, fontSize: headlineSize * 0.5, marginTop: 6 * u}}>{s.value}</div>
                  </div>
                </React.Fragment>
              );
            })}
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
