import React, {useMemo} from 'react';
import {AbsoluteFill} from 'remotion';
import {AnimatedText} from '../components/AnimatedText';
import {Particles} from '../components/Atmosphere';
import {SEED_PATH, Seed} from '../components/Seed';
import {copy} from '../content/copy';
import {ease, lerp, progress, tween} from '../utils/easing';
import {type Pt, pt, rand, smoothPath} from '../utils/geometry';
import {useLayout} from '../utils/layout';
import {useSceneFrame} from '../utils/scene';

/** Floating seed pose at the end of this scene; FinalReveal starts from it. */
export const RETURN_SEED_END = {size: 330, rotate: -4};

type SeedSpot = {p: Pt; angle: number; hero?: boolean};

/**
 * SCENE 08 · 0:35–0:40
 * Harvest → vegetable → seed. A ripe tomato turns in warm light; a blade of
 * light slices it, revealing the cross-section and its seeds. The camera
 * dives into one seed, everything else falls away, and it floats alone in
 * darkness: the same seed that opened the film.
 */
export const ReturnToSeed: React.FC = () => {
  const f = useSceneFrame();
  const {portrait, u, width, height, headlineSize, marginX, safeBottom} = useLayout();
  const C = pt(width / 2, height * (portrait ? 0.44 : 0.5));
  const R = (portrait ? 330 : 300) * u;

  const inP = tween(f, [-16, 6], [0, 1], ease.inOut);
  const cut = progress(f, 26, 20, ease.inOut);
  const dive = progress(f, 50, 50, ease.in);
  const heroIn = progress(f, 90, 14, ease.inOut);
  const pull = progress(f, 100, 50, ease.out);

  // Seeds in four locules, arranged around the placenta.
  const seeds = useMemo(() => {
    const out: SeedSpot[] = [];
    for (let l = 0; l < 4; l++) {
      const mid = -Math.PI / 4 + l * (Math.PI / 2);
      for (let j = 0; j < 7; j++) {
        const a = mid + (j - 3) * 0.17 + (rand(`ta${l}${j}`) - 0.5) * 0.06;
        const r = R * (0.42 + (j % 2) * 0.1 + rand(`tr${l}${j}`) * 0.04);
        out.push({p: pt(Math.cos(a) * r, Math.sin(a) * r), angle: (a * 180) / Math.PI + 90 + (rand(`tt${l}${j}`) - 0.5) * 30});
      }
    }
    out[3].hero = true;
    return out;
  }, [R]);
  const hero = seeds.find((s) => s.hero)!;
  const seedLen = R * 0.085;

  // Camera dive toward the hero seed, rotating it upright.
  const Sf = (660 * u) / seedLen;
  const S = Math.exp(lerp(0, Math.log(Sf), dive));
  // Frame the hero seed first, then zoom (otherwise it drifts off-centre during the dive).
  const aim = progress(f, 44, 40, ease.inOut);
  const focus = pt(lerp(0, hero.p.x, aim), lerp(0, hero.p.y, aim));
  const rot = lerp(0, -hero.angle, aim);
  const tomatoRot = lerp(-8, 6, progress(f, -16, 60, ease.gentle));

  // Floating hero seed after the dive.
  const heroSize = lerp(660, RETURN_SEED_END.size, pull) * u;
  const bob = Math.sin(f / 16) * 6 * u * pull;

  const septa = [0, 1, 2, 3].map((i) => (Math.PI / 2) * i);

  return (
    <AbsoluteFill>
      <AbsoluteFill
        style={{
          opacity: inP,
          background: `radial-gradient(ellipse 60% 70% at 50% ${(C.y / height) * 100}%, #2A160C 0%, #120904 45%, #030201 100%)`,
        }}
      />
      <svg width={width} height={height} style={{position: 'absolute', inset: 0, opacity: inP * (1 - heroIn)}}>
        <defs>
          <radialGradient id="rt-skin" cx="0.36" cy="0.3" r="0.8">
            <stop offset="0" stopColor="#FF8A66" />
            <stop offset="0.35" stopColor="#D7331F" />
            <stop offset="0.8" stopColor="#8E160B" />
            <stop offset="1" stopColor="#3E0703" />
          </radialGradient>
          <radialGradient id="rt-flesh" cx="0.5" cy="0.5" r="0.5">
            <stop offset="0.6" stopColor="#E95238" />
            <stop offset="0.93" stopColor="#D8361F" />
            <stop offset="1" stopColor="#9E1C0E" />
          </radialGradient>
          <radialGradient id="rt-gel" cx="0.5" cy="0.5" r="0.6">
            <stop offset="0" stopColor="#F9B070" stopOpacity="0.95" />
            <stop offset="1" stopColor="#E0663E" stopOpacity="0.9" />
          </radialGradient>
          <radialGradient id="rt-spec" cx="0.5" cy="0.5" r="0.5">
            <stop offset="0" stopColor="#FFFFFF" stopOpacity="0.9" />
            <stop offset="1" stopColor="#FFFFFF" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="rt-seed" cx="0.38" cy="0.3" r="0.8">
            <stop offset="0" stopColor="#FFF6E0" />
            <stop offset="0.5" stopColor="#EAD3A0" />
            <stop offset="1" stopColor="#B7925A" />
          </radialGradient>
          <filter id="rt-flesh-tex" x="0" y="0" width="100%" height="100%">
            <feTurbulence type="fractalNoise" baseFrequency={0.02 / S} numOctaves={3} seed={12} />
            <feColorMatrix type="matrix" values="0 0 0 0 1  0 0 0 0 0.85  0 0 0 0 0.7  0 0 0 0.9 -0.3" />
          </filter>
          <clipPath id="rt-blade-clip">
            <circle cx={C.x} cy={C.y} r={R * 1.12} />
          </clipPath>
          <clipPath id="rt-circle">
            <circle r={R} />
          </clipPath>
          <linearGradient id="rt-cutmask-g" x1="0" y1="0" x2="0" y2="1">
            <stop offset={Math.max(0, cut * 1.2 - 0.12)} stopColor="#fff" />
            <stop offset={Math.min(1, cut * 1.2)} stopColor="#000" />
          </linearGradient>
          <mask id="rt-cutmask" maskContentUnits="objectBoundingBox">
            <rect width="1" height="1" fill="url(#rt-cutmask-g)" />
          </mask>
          <filter id="rt-soft" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation={3 * u} />
          </filter>
          <filter id="rt-dof" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation={(dive * 9 * u) / S} />
          </filter>
        </defs>

        <g transform={`translate(${C.x} ${C.y}) rotate(${rot}) scale(${S}) translate(${-focus.x} ${-focus.y})`}>
          {/* Whole tomato (before the cut) */}
          <g opacity={1 - cut} transform={`rotate(${tomatoRot})`}>
            <path
              d={smoothPath(Array.from({length: 60}, (_, j) => {
                const a = (j / 60) * Math.PI * 2;
                const r = R * (1 + 0.03 * Math.cos(5 * a));
                return pt(Math.cos(a) * r * 1.04, Math.sin(a) * r * 0.94);
              }), true)}
              fill="url(#rt-skin)"
            />
            <path
              d={smoothPath(Array.from({length: 12}, (_, j) => {
                const a = (j / 12) * Math.PI * 2 + 0.2;
                const r = j % 2 === 0 ? R * 0.34 : R * 0.1;
                return pt(Math.cos(a) * r, -R * 0.8 + Math.sin(a) * r * 0.45);
              }), true, 0.35)}
              fill="#3E6B2A"
            />
            <path d={`M0,${-R * 0.82} q${R * 0.03},${-R * 0.16} ${R * 0.12},${-R * 0.2}`} stroke="#5C7A34" strokeWidth={R * 0.05} strokeLinecap="round" fill="none" />
            <ellipse cx={-R * 0.35} cy={-R * 0.38} rx={R * 0.22} ry={R * 0.12} fill="url(#rt-spec)" opacity={0.6} transform={`rotate(-30 ${-R * 0.35} ${-R * 0.38})`} />
            <ellipse cx={0} cy={0} rx={R * 1.04} ry={R * 0.94} fill="none" stroke="#FFC08A" strokeOpacity={0.3} strokeWidth={3 * u} filter="url(#rt-soft)" />
          </g>

          {/* Cross-section, revealed by the blade of light */}
          <g mask="url(#rt-cutmask)" filter={dive > 0.02 ? 'url(#rt-dof)' : undefined}>
            <circle r={R} fill="url(#rt-flesh)" />
            <circle r={R} fill="none" stroke="#7A0F07" strokeWidth={R * 0.035} />
            {/* Locules (gel chambers) between the septa */}
            {septa.map((a0, i) => {
              const a = a0 + Math.PI / 4;
              const pts = Array.from({length: 24}, (_, j) => {
                const t = j / 23;
                const ang = a - 0.62 + t * 1.24;
                const rOuter = R * (0.76 + 0.03 * Math.sin(t * Math.PI * 3 + i));
                return pt(Math.cos(ang) * rOuter, Math.sin(ang) * rOuter);
              });
              const inner = Array.from({length: 12}, (_, j) => {
                const t = 1 - j / 11;
                const ang = a - 0.5 + t * 1.0;
                return pt(Math.cos(ang) * R * 0.28, Math.sin(ang) * R * 0.28);
              });
              return <path key={i} d={smoothPath([...pts, ...inner], true, 0.4)} fill="url(#rt-gel)" />;
            })}
            {/* Columella / placenta */}
            <path
              d={smoothPath(Array.from({length: 16}, (_, j) => {
                const a = (j / 16) * Math.PI * 2;
                const r = R * (0.22 + 0.05 * Math.cos(a * 4));
                return pt(Math.cos(a) * r, Math.sin(a) * r);
              }), true)}
              fill="#F07A55"
            />
            {/* Fleshy texture and inner shading toward the skin */}
            <g clipPath="url(#rt-circle)">
              <rect x={-R} y={-R} width={R * 2} height={R * 2} filter="url(#rt-flesh-tex)" opacity={0.25} style={{mixBlendMode: 'soft-light'}} />
              <circle r={R * 1.02} fill="none" stroke="#5A0A04" strokeOpacity={0.45} strokeWidth={R * 0.12} filter="url(#rt-soft)" />
            </g>
            <circle r={R * 0.985} fill="none" stroke="#FFB38F" strokeOpacity={0.35} strokeWidth={R * 0.012} />
            {/* Seeds with gel halos */}
            {seeds.filter((s) => !s.hero).map((s, i) => (
              <g key={i} transform={`translate(${s.p.x} ${s.p.y}) rotate(${s.angle}) scale(${seedLen / 150}) translate(-50 -80)`}>
                <path d={SEED_PATH} fill="#FFE0B0" opacity={0.35} transform="translate(50 80) scale(1.35) translate(-50 -80)" />
                <path d={SEED_PATH} fill="url(#rt-seed)" stroke="#B89A5E" strokeWidth={4} />
              </g>
            ))}
            {/* Wet highlights */}
            {[pt(-0.4, -0.5), pt(0.3, -0.2), pt(-0.1, 0.45)].map((p, i) => (
              <ellipse key={i} cx={p.x * R} cy={p.y * R} rx={R * 0.07} ry={R * 0.025} fill="url(#rt-spec)" opacity={0.55} transform={`rotate(${-30 + i * 20} ${p.x * R} ${p.y * R})`} />
            ))}
          </g>
          {/* Hero seed stays sharp while everything else falls out of focus */}
          <g mask="url(#rt-cutmask)" transform={`translate(${hero.p.x} ${hero.p.y}) rotate(${hero.angle}) scale(${seedLen / 150}) translate(-50 -80)`}>
            <path d={SEED_PATH} fill="#FFE0B0" opacity={0.35 * (1 - dive)} transform="translate(50 80) scale(1.35) translate(-50 -80)" />
            <path d={SEED_PATH} fill="url(#rt-seed)" stroke="#B89A5E" strokeWidth={4 / Math.max(1, S * 0.2)} />
          </g>
        </g>

        {/* The blade of light */}
        {cut > 0 && cut < 1 ? (
          <g opacity={Math.sin(Math.PI * cut)} clipPath="url(#rt-blade-clip)">
            <rect x={C.x - R * 1.4} y={C.y - R + cut * 1.2 * 2 * R - 3 * u} width={R * 2.8} height={6 * u} fill="#FFF3DC" filter="url(#rt-soft)" />
            <rect x={C.x - R * 1.3} y={C.y - R + cut * 1.2 * 2 * R - 1 * u} width={R * 2.6} height={2 * u} fill="#FFFFFF" />
          </g>
        ) : null}
      </svg>

      {/* The hero seed, alone in the dark */}
      {heroIn > 0 ? (
        <AbsoluteFill style={{background: `rgba(2,3,2,${heroIn})`}}>
          <Particles seed="r-dust" count={24} size={[2, 8]} drift={{x: 3, y: -5}} opacity={0.35 * heroIn} />
          <div
            style={{
              position: 'absolute',
              left: C.x,
              top: C.y + bob,
              transform: `translate(-50%, -50%) rotate(${lerp(0, RETURN_SEED_END.rotate, pull)}deg)`,
              opacity: heroIn,
            }}
          >
            <Seed id="s8-seed" size={heroSize} lightX={lerp(0.3, 0.38, pull)} lightY={0.28} keyLight={lerp(1, 0.85, pull)} rimLight={0.95} blur={(1 - heroIn) * 6 * u} />
          </div>
        </AbsoluteFill>
      ) : null}

      {copy.returnToSeed.line ? (
        <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: safeBottom, paddingLeft: marginX, paddingRight: marginX}}>
          <AnimatedText text={copy.returnToSeed.line} start={108} exit={140} size={headlineSize * 0.8} align="center" />
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  );
};
