import React, {useMemo} from 'react';
import {AbsoluteFill} from 'remotion';
import {AnimatedText} from '../components/AnimatedText';
import {Bokeh, LightLeak, Particles} from '../components/Atmosphere';
import {CinematicImage} from '../components/CinematicImage';
import {getSlot, type SlotId} from '../assets/useSlot';
import {copy} from '../content/copy';
import {ease, envelope, lerp, progress, tween} from '../utils/easing';
import {type Pt, add, pt, quad, rand, ribbon, rotate, smoothPath} from '../utils/geometry';
import {useLayout} from '../utils/layout';
import {useSceneFrame} from '../utils/scene';
import {leafGeometry} from '../visuals/leaf';

type Branch = {a: Pt; c: Pt; b: Pt; depth: number; leaves: number; fruits: number; seed: string};

/** Backlit chilli branch: silhouetted stem, translucent leaves, glowing pods. */
const BranchView: React.FC<{br: Branch; W: number; H: number; u: number; sun: Pt; sway: number}> = ({br, W, H, u, sun, sway}) => {
  const A = pt(br.a.x * W, br.a.y * H);
  const C = pt(br.c.x * W, br.c.y * H);
  const B = pt(br.b.x * W, br.b.y * H);
  const at = (t: number) => quad(A, C, B, t);
  const sc = (1.45 - br.depth * 0.55) * u;
  const leaf = leafGeometry(170 * sc, 70 * sc, 0.14, 4);
  const stem = Array.from({length: 30}, (_, i) => at(i / 29));
  const glowFor = (p: Pt) => Math.max(0, 1 - Math.hypot(p.x - sun.x, p.y - sun.y) / (0.8 * W));
  return (
    <g>
      <path d={smoothPath(stem)} stroke="#140F06" strokeWidth={10 * sc} fill="none" strokeLinecap="round" />
      <path d={smoothPath(stem)} stroke="#FFD08A" strokeOpacity={0.55} strokeWidth={2.2 * sc} fill="none" transform={`translate(${2.5 * sc} ${-2.5 * sc})`} />
      {Array.from({length: br.leaves}, (_, i) => {
        const t = 0.12 + (i / br.leaves) * 0.88;
        const base = at(t);
        const side = i % 2 ? 1 : -1;
        const ang = side * (0.95 + rand(`${br.seed}la${i}`) * 0.5) + sway * (1 + i * 0.1) - 0.25;
        const g = glowFor(base);
        const pts = leaf.outline.map((p) => add(base, rotate(p, ang)));
        const d = smoothPath(pts, true);
        return (
          <g key={i}>
            <path d={d} fill="url(#h-leaf-dark)" />
            <path d={d} fill="url(#h-leaf-lit)" opacity={0.8 * Math.pow(g, 1.6)} />
            {leaf.veins.map((v, j) => (
              <path key={j} d={smoothPath(v.map((p) => add(base, rotate(p, ang))))} stroke="#EAF2A8" strokeOpacity={0.12 + 0.35 * g} strokeWidth={1.1 * sc} fill="none" />
            ))}
            <path d={smoothPath(leaf.midrib.map((p) => add(base, rotate(p, ang))))} stroke="#F2F6BE" strokeOpacity={0.25 + 0.45 * g} strokeWidth={2 * sc} fill="none" />
            <path d={d} fill="none" stroke="#FFD99A" strokeOpacity={0.35 + 0.5 * g} strokeWidth={1.8 * sc} />
          </g>
        );
      })}
      {Array.from({length: br.fruits}, (_, i) => {
        const t = 0.28 + (i / Math.max(1, br.fruits)) * 0.62;
        const base = add(at(t), pt(0, 4 * sc));
        const len = (150 + rand(`${br.seed}fl${i}`) * 80) * sc;
        const lean = (rand(`${br.seed}fa${i}`) - 0.5) * 0.45 + sway * 0.6;
        const tip = add(base, rotate(pt(0, len), lean));
        const ctrl = add(base, rotate(pt(len * 0.2, len * 0.55), lean));
        const pod = Array.from({length: 24}, (_, j) => quad(base, ctrl, tip, j / 23));
        const outline = ribbon(pod, (q) => 14 * sc * Math.pow(Math.max(0, 1 - Math.pow(q, 1.7)), 0.7) * (q < 0.08 ? 0.75 + 3 * q : 1));
        const g = glowFor(base);
        return (
          <g key={`f${i}`}>
            <path d={smoothPath(outline, true)} fill="#FF5A2E" opacity={0.35 + 0.35 * g} filter="url(#h-podglow)" />
            <path d={smoothPath(outline, true)} fill="url(#h-pod)" />
            <path d={smoothPath(pod.slice(2, 17))} stroke="#FFD2B4" strokeOpacity={0.55 + 0.3 * g} strokeWidth={2.4 * sc} strokeLinecap="round" fill="none" transform={`translate(${-4 * sc} 0)`} />
            <ellipse cx={base.x} cy={base.y} rx={10 * sc} ry={7 * sc} fill="#2A4418" />
          </g>
        );
      })}
    </g>
  );
};

/**
 * SCENE 07 · 0:29–0:35
 * Human impact. Golden hour through a healthy chilli crop: backlit leaves,
 * glowing pods, pollen in the light. Real farmer / hands / basket footage
 * (never invented people) drops in via asset slots when supplied.
 */
export const FarmerHarvest: React.FC = () => {
  const f = useSceneFrame();
  const {portrait, u, width, height, marginX, headlineSize, supportSize, safeBottom} = useLayout();
  const sun = portrait ? pt(width * 0.62, height * 0.3) : pt(width * 0.7, height * 0.34);
  const inP = tween(f, [-18, 4], [0, 1], ease.inOut);
  const truck = progress(f, -18, 198, ease.gentle);
  const sway = Math.sin(f / 22) * 0.04;

  const branches: Branch[] = useMemo(
    () =>
      portrait
        ? [
            {a: pt(0.05, 0.62), c: pt(0.4, 0.5), b: pt(0.62, 0.36), depth: 0.9, leaves: 7, fruits: 4, seed: 'm1'},
            {a: pt(-0.1, 1.05), c: pt(0.2, 0.8), b: pt(0.45, 0.66), depth: 0.2, leaves: 8, fruits: 3, seed: 'n1'},
            {a: pt(1.1, 0.95), c: pt(0.85, 0.75), b: pt(0.7, 0.58), depth: 0.3, leaves: 7, fruits: 3, seed: 'n2'},
          ]
        : [
            {a: pt(0.3, 1.05), c: pt(0.42, 0.72), b: pt(0.6, 0.5), depth: 0.9, leaves: 7, fruits: 5, seed: 'm1'},
            {a: pt(-0.06, 1.08), c: pt(0.1, 0.75), b: pt(0.28, 0.55), depth: 0.15, leaves: 8, fruits: 3, seed: 'n1'},
            {a: pt(1.08, 1.05), c: pt(0.92, 0.72), b: pt(0.8, 0.52), depth: 0.3, leaves: 7, fruits: 3, seed: 'n2'},
          ],
    [portrait],
  );

  const photoIds: SlotId[] = ['harvest-farmer', 'harvest-hands', 'harvest-basket'];
  const photos = photoIds.map((id) => getSlot(id));

  return (
    <AbsoluteFill style={{opacity: inP}}>
      {/* Sky and far field */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 85% 80% at ${(sun.x / width) * 100}% ${(sun.y / height) * 100}%, #FFF0CC 0%, #F6C57A 16%, #D08A45 40%, #6A4420 70%, #24170A 100%)`,
        }}
      />
      <svg width={width} height={height} style={{position: 'absolute', inset: 0}}>
        <defs>
          <filter id="h-far" x="-10%" y="-10%" width="120%" height="120%">
            <feGaussianBlur stdDeviation={10 * u} />
          </filter>
          <filter id="h-near" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation={5 * u} />
          </filter>
          <radialGradient id="h-leaf-dark" cx="0.5" cy="0.45" r="0.6">
            <stop offset="0" stopColor="#1C3012" />
            <stop offset="1" stopColor="#070D05" />
          </radialGradient>
          <radialGradient id="h-leaf-lit" cx="0.5" cy="0.4" r="0.65">
            <stop offset="0" stopColor="#C7D774" />
            <stop offset="0.5" stopColor="#6F9234" />
            <stop offset="1" stopColor="#233C14" />
          </radialGradient>
          <linearGradient id="h-pod" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="#6E0E07" />
            <stop offset="0.35" stopColor="#E0452A" />
            <stop offset="0.6" stopColor="#FF7A4E" />
            <stop offset="1" stopColor="#8A1409" />
          </linearGradient>
          <filter id="h-podglow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation={8 * u} />
          </filter>
          <linearGradient id="h-ray" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="#FFE4B0" stopOpacity="0.5" />
            <stop offset="1" stopColor="#FFE4B0" stopOpacity="0" />
          </linearGradient>
          <radialGradient id="h-sun" cx="0.5" cy="0.5" r="0.5">
            <stop offset="0" stopColor="#FFFBEF" stopOpacity="1" />
            <stop offset="0.1" stopColor="#FFF0C8" stopOpacity="0.9" />
            <stop offset="0.35" stopColor="#F9C878" stopOpacity="0.35" />
            <stop offset="1" stopColor="#F9C878" stopOpacity="0" />
          </radialGradient>
        </defs>
        {/* Far crop band, defocused */}
        <g filter="url(#h-far)" transform={`translate(${lerp(10, -10, truck) * u} 0)`}>
          {Array.from({length: 26}, (_, i) => {
            const x = (i / 25) * width * 1.1 - width * 0.05;
            const y = height * (portrait ? 0.5 : 0.62) + rand(`fb${i}`) * 20 * u;
            const r = (60 + rand(`fr${i}`) * 70) * u;
            return <ellipse key={i} cx={x} cy={y} rx={r} ry={r * 0.6} fill="#241A0C" opacity={0.85} />;
          })}
          <rect x={-50} y={height * (portrait ? 0.52 : 0.64)} width={width + 100} height={height} fill="#1A1208" />
        </g>
        {/* Soft god rays from the sun */}
        <g style={{mixBlendMode: 'screen'}} opacity={0.5}>
          {[-0.5, -0.2, 0.15, 0.45, 0.8].map((a, i) => (
            <rect
              key={i}
              x={sun.x}
              y={sun.y - 30 * u}
              width={width * 1.2}
              height={(40 + i * 18) * u}
              fill="url(#h-ray)"
              transform={`rotate(${(a + 1.57 + Math.sin(f / 60 + i) * 0.02) * 57.3} ${sun.x} ${sun.y})`}
              opacity={0.35}
            />
          ))}
        </g>
        {/* Mid branch (in focus) */}
        <g transform={`translate(${lerp(30, -50, truck) * u} ${lerp(10, -10, truck) * u})`}>
          <BranchView br={branches[0]} W={width} H={height} u={u} sun={sun} sway={sway} />
        </g>
        {/* Foreground branches (shallow depth of field) */}
        <g filter="url(#h-near)" transform={`translate(${lerp(80, -120, truck) * u} ${lerp(20, -20, truck) * u})`}>
          <BranchView br={branches[1]} W={width} H={height} u={u} sun={sun} sway={sway * 1.3} />
          <BranchView br={branches[2]} W={width} H={height} u={u} sun={sun} sway={-sway} />
        </g>
        {/* Sun bloom over everything */}
        <circle cx={sun.x} cy={sun.y} r={420 * u * (1 + 0.04 * Math.sin(f / 18))} fill="url(#h-sun)" style={{mixBlendMode: 'screen'}} />
      </svg>

      {/* Real photography, when supplied, plays in thirds over the bed */}
      {photos.map((p, i) =>
        p ? (
          <AbsoluteFill key={i} style={{opacity: envelope(f, i * 60 - 8, 16, (i + 1) * 60 - 4, 16, ease.inOut, ease.inOut)}}>
            <CinematicImage src={p.src} kind={p.kind === 'video' ? 'video' : 'image'} frame={f - i * 60} duration={72} grade="warm" />
          </AbsoluteFill>
        ) : null,
      )}

      <Bokeh seed="h-bokeh" count={10} colors={['255,214,150', '255,190,120']} radius={[20, 70]} opacity={0.35} shiftX={lerp(40, -60, truck) * u} area={{x: sun.x - 500 * u, y: sun.y - 300 * u, w: 1000 * u, h: 600 * u}} />
      <Particles seed="h-pollen" count={40} size={[2, 10]} drift={{x: -10, y: -8}} opacity={0.7} focus={0.4} color="255,224,160" />
      <LightLeak opacity={0.25 + 0.1 * Math.sin(f / 25)} x={sun.x / width} y={sun.y / height} size={0.8} />

      <AbsoluteFill
        style={{
          background: portrait
            ? 'linear-gradient(to top, rgba(12,8,4,0.8) 0%, rgba(12,8,4,0.25) 32%, rgba(0,0,0,0) 50%)'
            : 'linear-gradient(to top, rgba(12,8,4,0.7) 0%, rgba(12,8,4,0.2) 30%, rgba(0,0,0,0) 45%)',
        }}
      />
      <AbsoluteFill
        style={{
          justifyContent: 'flex-end',
          alignItems: 'center',
          paddingLeft: marginX,
          paddingRight: marginX,
          paddingBottom: portrait ? safeBottom : safeBottom * 1.05,
        }}
      >
        <AnimatedText text={copy.harvest.headline} start={16} exit={160} size={headlineSize} align="center" style={{textShadow: '0 2px 30px rgba(0,0,0,0.5)'}} />
        <AnimatedText
          text={copy.harvest.support}
          start={62}
          exit={160}
          variant="support"
          mode="fade"
          size={supportSize * 1.1}
          align="center"
          style={{marginTop: 16 * u, color: 'rgba(250,240,220,0.85)', textShadow: '0 1px 18px rgba(0,0,0,0.6)'}}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
