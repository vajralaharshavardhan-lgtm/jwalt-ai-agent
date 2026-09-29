import React, {useMemo} from 'react';
import {AbsoluteFill} from 'remotion';
import {Delaunay} from 'd3-delaunay';
import {AnimatedText} from '../components/AnimatedText';
import {CinematicImage} from '../components/CinematicImage';
import {SEED_PATH} from '../components/Seed';
import {getSlot} from '../assets/useSlot';
import {copy} from '../content/copy';
import {palette} from '../styles/brand';
import {ease, lerp, progress, smoothstep, tween} from '../utils/easing';
import {type Pt, add, centroid, linePath, pt, rand, rotate, smoothPath} from '../utils/geometry';
import {useLayout} from '../utils/layout';
import {useSceneFrame} from '../utils/scene';
import {seedBaseSize, seedCenterY} from './OpeningSeed';
import {GERM_CAMERA_END, SEED_REST_ROT, cotyledonRotations, cotyledonShape, seedlingGeometry} from '../visuals/seedling';
import {leafGeometry} from '../visuals/leaf';

const INK = palette.cream;
const GOLD = palette.husk;

/** Stroke that draws on: progress 0..1 via normalised dash. */
const Draw: React.FC<{
  d: string;
  p: number;
  color?: string;
  width?: number;
  opacity?: number;
  fill?: string;
  dash?: string;
  /** Current transform scale, so line weight stays constant on screen. */
  s?: number;
}> = ({d, p, color = INK, width = 1.4, opacity = 0.9, fill = 'none', dash, s = 1}) =>
  p <= 0 ? null : (
    <path
      d={d}
      fill={fill}
      stroke={color}
      strokeWidth={width / s}
      strokeOpacity={opacity}
      strokeLinecap="round"
      strokeLinejoin="round"
      pathLength={dash ? undefined : 1}
      strokeDasharray={dash ?? '1 1'}
      strokeDashoffset={dash ? undefined : 1 - p}
      opacity={dash ? p : 1}
    />
  );

/**
 * SCENE 03 · 0:08–0:13
 * The photoreal seedling is traced into a breeder's botanical plate: the
 * soil dissolves to deep green, a measurement grid draws in, the plant grows
 * true leaves in line-art, a leaf-cell micrograph and an F1 cross diagram
 * annotate it. Ends by pushing into a leaf (hand-off to Field Validation).
 */
export const Research: React.FC = () => {
  const f = useSceneFrame();
  const L = useLayout();
  const {portrait, u, width, height, cx, marginX, headlineSize, supportSize, monoSize, safeBottom} = L;
  const size = seedBaseSize(portrait, u);
  const sy = seedCenterY(portrait, height);
  const geo = seedlingGeometry(size);
  const {k} = geo;
  const photo = getSlot('research-breeder');

  // Plate layout (screen space).
  const plant = portrait ? pt(width * 0.34, height * 0.45) : pt(width * 0.6, height * 0.64);
  const plateScale = portrait ? 0.34 : 0.33;
  const micro = portrait
    ? {x: width * 0.73, y: height * 0.26, r: 165 * u}
    : {x: width * 0.83, y: height * 0.36, r: 185 * u};
  const cross = portrait ? pt(width * 0.73, height * 0.43) : pt(width * 0.83, height * 0.74);

  // True leaves grow from the shoot tip.
  const shootTip = geo.shoot[geo.shoot.length - 1];
  const leafGrow = progress(f, 6, 70, ease.out);
  const leafL = 360 * k;
  // Internode: true leaves sit above the cotyledons.
  const internode = 190 * k;
  const nodeTop = pt(shootTip.x + 6 * k, shootTip.y - internode * leafGrow);
  const leaf = useMemo(() => leafGeometry(leafL, leafL * 0.36, 0.1, 6), [leafL]);
  const leafAngles = [-0.62, 0.56];
  // Short petiole lifts each leaf clear of the cotyledons.
  const petiole = 40 * k;
  const leafWorld = (i: number, p: Pt) =>
    add(nodeTop, rotate(pt(p.x * leafGrow, (p.y - petiole) * leafGrow), leafAngles[i]));
  // Point the camera pushes into at the end: middle of the right leaf.
  const target = leafWorld(1, leaf.mid(0.5));

  // Camera: start exactly where Germination ended, settle into the plate, then push into the leaf.
  const settle = progress(f, -4, 50, ease.cinematic);
  const push = progress(f, 116, 34, ease.in);
  const startOrigin = pt(cx, sy + GERM_CAMERA_END.offsetY * height);
  const plateOrigin = plant;
  let scale = lerp(GERM_CAMERA_END.scale, plateScale, settle);
  let origin = pt(lerp(startOrigin.x, plateOrigin.x, settle), lerp(startOrigin.y, plateOrigin.y, settle));
  if (push > 0) {
    const endScale = 3.4 * (portrait ? 1.3 : 1);
    const endOrigin = pt(width / 2 - target.x * endScale, height / 2 - target.y * endScale);
    scale = lerp(scale, endScale, push);
    origin = pt(lerp(origin.x, endOrigin.x, push), lerp(origin.y, endOrigin.y, push));
  }
  const toScreen = (p: Pt) => pt(origin.x + p.x * scale, origin.y + p.y * scale);

  const bgIn = tween(f, [-20, -2], [0, 1], ease.inOut);
  const trace = progress(f, -20, 22, ease.out);
  const gridIn = progress(f, 0, 40, ease.out);
  const plateOut = 1 - progress(f, 112, 26, ease.in);
  const microP = progress(f, 30, 50, ease.out);
  const crossP = progress(f, 52, 40, ease.out);

  // Micrograph cells (static per layout).
  const cells = useMemo(() => {
    const R = micro.r;
    const pts: [number, number][] = [];
    const step = R / 5.2;
    for (let gx = -R - step; gx <= R + step; gx += step) {
      for (let gy = -R - step; gy <= R + step; gy += step * 0.8) {
        const j = `${Math.round(gx)}-${Math.round(gy)}`;
        pts.push([gx + (rand(`cx${j}`) - 0.5) * step * 0.8, gy + (rand(`cy${j}`) - 0.5) * step * 0.7]);
      }
    }
    const vor = Delaunay.from(pts).voronoi([-R * 1.2, -R * 1.2, R * 1.2, R * 1.2]);
    return pts.map((_, i) => {
      const poly = (vor.cellPolygon(i) ?? []).map(([x, y]) => pt(x, y));
      return {poly, c: poly.length ? centroid(poly) : pt(0, 0), stoma: rand(`st${i}`) < 0.14, a: rand(`sa${i}`) * Math.PI};
    });
  }, [micro.r]);

  const cot = cotyledonShape(300 * k);
  const [rotL, rotR] = cotyledonRotations(1);
  const leafAnchor = toScreen(leafWorld(1, leaf.mid(0.62)));
  const leaderEnd = pt(micro.x - micro.r * 0.92, micro.y + micro.r * 0.38);
  const leaderP = progress(f, 44, 26, ease.inOut);

  return (
    <AbsoluteFill>
      {/* Deep-green plate */}
      <AbsoluteFill
        style={{
          opacity: bgIn,
          background: `radial-gradient(ellipse 80% 90% at ${portrait ? '50% 35%' : '65% 45%'}, #13362A 0%, #0B2118 50%, #04100A 100%)`,
        }}
      />
      {photo ? (
        <AbsoluteFill
          style={{
            opacity: bgIn * tween(f, [0, 30], [0, 1]) * plateOut,
            WebkitMaskImage: portrait
              ? 'linear-gradient(to bottom, black 0%, black 45%, transparent 65%)'
              : 'linear-gradient(to right, transparent 30%, black 60%)',
          }}
        >
          <CinematicImage src={photo.src} kind={photo.kind === 'video' ? 'video' : 'image'} frame={f + 20} duration={170} grade="cool" vignette={0.6} />
        </AbsoluteFill>
      ) : null}

      <svg width={width} height={height} style={{position: 'absolute', inset: 0}}>
        <defs>
          <pattern id="r-grid" width={64 * u} height={64 * u} patternUnits="userSpaceOnUse">
            <path d={`M${64 * u},0L0,0L0,${64 * u}`} fill="none" stroke={INK} strokeOpacity={0.06} strokeWidth={1} />
          </pattern>
          <linearGradient id="r-grid-mask-g" x1="0" y1="0" x2="1" y2="0">
            <stop offset={Math.max(0, gridIn * 1.2 - 0.2)} stopColor="#fff" />
            <stop offset={Math.min(1, gridIn * 1.2)} stopColor="#fff" stopOpacity="0" />
          </linearGradient>
          <mask id="r-grid-mask">
            <rect width={width} height={height} fill="url(#r-grid-mask-g)" />
          </mask>
          <clipPath id="r-micro-clip">
            <circle cx={0} cy={0} r={micro.r} />
          </clipPath>
        </defs>

        <g opacity={bgIn * plateOut}>
          <rect width={width} height={height} fill="url(#r-grid)" mask="url(#r-grid-mask)" />
        </g>

        {/* The plant in world space */}
        <g transform={`translate(${origin.x} ${origin.y}) scale(${scale})`}>
          <g transform={`rotate(${SEED_REST_ROT}) scale(${size / 160}) translate(-50 -80)`}>
            <Draw d={SEED_PATH} p={trace} width={1.4} opacity={0.85} s={(scale * size) / 160} />
          </g>
          <Draw s={scale} d={smoothPath(geo.root)} p={trace} width={1.4} opacity={0.75} />
          {geo.laterals.map((lat, i) => {
            const base = geo.root[Math.floor(lat.at * (geo.root.length - 1))];
            const pts = lat.pts.map((p) => add(base, pt(p.x * lat.side, p.y)));
            return <Draw s={scale} key={i} d={smoothPath(pts)} p={progress(f, 10 + i * 8, 40, ease.out)} width={1} opacity={0.5} />;
          })}
          <Draw s={scale} d={smoothPath(geo.shoot)} p={trace} width={1.5} opacity={0.9} />
          <Draw s={scale} d={linePath([shootTip, nodeTop])} p={leafGrow} width={1.5} opacity={0.9} />
          {[rotL, rotR].map((r, i) => (
            <Draw s={scale} key={i} d={smoothPath(cot.map((p) => add(shootTip, rotate(p, r))), true)} p={trace} width={1.4} opacity={0.9} />
          ))}
          {/* True leaves, line-art, with venation */}
          {leafAngles.map((_, i) => (
            <g key={i}>
              <Draw s={scale} d={linePath([nodeTop, leafWorld(i, pt(0, 0))])} p={progress(f, 6, 20, ease.out)} width={1.4} opacity={0.9} />
              <Draw s={scale} d={smoothPath(leaf.outline.map((p) => leafWorld(i, p)), true)} p={progress(f, 8 + i * 6, 56, ease.out)} width={1.5} opacity={0.95} />
              <Draw s={scale} d={smoothPath(leaf.midrib.map((p) => leafWorld(i, p)))} p={progress(f, 16 + i * 6, 44, ease.out)} width={1.2} color={GOLD} opacity={0.9} />
              {leaf.veins.map((v, j) => (
                <Draw
                  key={j}
                  d={smoothPath(v.map((p) => leafWorld(i, p)))}
                  p={progress(f, 26 + i * 6 + j * 2, 30, ease.out)}
                  width={0.9}
                  color={GOLD}
                  opacity={0.6}
                />
              ))}
            </g>
          ))}
        </g>

        <g opacity={plateOut}>
          {/* Dimension line beside the plant */}
          {(() => {
            const top = toScreen(pt(nodeTop.x, nodeTop.y - leafL * 0.95));
            const bottom = toScreen(pt(0, 90 * k));
            const x = toScreen(pt(-560 * k, 0)).x;
            const p = progress(f, 34, 40, ease.out);
            const ticks = 9;
            return (
              <g opacity={0.75}>
                <Draw d={linePath([pt(x, bottom.y), pt(x, top.y)])} p={p} width={1} color={GOLD} />
                {Array.from({length: ticks + 1}, (_, i) => {
                  const y = lerp(bottom.y, top.y, i / ticks);
                  const w = i % 3 === 0 ? 14 * u : 7 * u;
                  return <Draw key={i} d={linePath([pt(x - w, y), pt(x, y)])} p={progress(f, 40 + i * 2, 12)} width={1} color={GOLD} />;
                })}
                <text
                  x={x - 22 * u}
                  y={top.y - 18 * u}
                  fill={INK}
                  fillOpacity={0.55 * progress(f, 50, 20)}
                  style={{font: `${monoSize}px "PS Mono"`, letterSpacing: '0.14em'}}
                >
                  FIG. 01
                </text>
              </g>
            );
          })()}

          {/* Leader from leaf to micrograph */}
          <circle cx={leafAnchor.x} cy={leafAnchor.y} r={4 * u} fill={GOLD} opacity={leaderP} />
          <Draw d={linePath([leafAnchor, pt(leafAnchor.x + (leaderEnd.x - leafAnchor.x) * 0.55, leaderEnd.y), leaderEnd])} p={leaderP} width={1} color={GOLD} opacity={0.8} />

          {/* Micrograph: leaf epidermis cells and stomata */}
          <g transform={`translate(${micro.x} ${micro.y})`}>
            <circle r={micro.r} fill="#0A1C14" opacity={0.85 * microP} />
            <g clipPath="url(#r-micro-clip)">
              {cells.map((c, i) => {
                const d = Math.hypot(c.c.x, c.c.y) / micro.r;
                const o = smoothstep(d - 0.15, d + 0.05, microP * 1.3);
                if (o <= 0 || c.poly.length < 3) {
                  return null;
                }
                return (
                  <g key={i} opacity={o}>
                    <path d={smoothPath(c.poly, true, 0.25)} fill={palette.leaf} fillOpacity={0.14} stroke={palette.sprout} strokeOpacity={0.55} strokeWidth={1.1} />
                    {c.stoma ? (
                      <g transform={`translate(${c.c.x} ${c.c.y}) rotate(${(c.a * 180) / Math.PI})`}>
                        <ellipse rx={9 * u} ry={5.5 * u} fill="none" stroke={palette.huskLight} strokeOpacity={0.8} strokeWidth={1.1} />
                        <path d={`M${-6 * u},0L${6 * u},0`} stroke={palette.huskLight} strokeOpacity={0.8} strokeWidth={1} />
                      </g>
                    ) : null}
                  </g>
                );
              })}
            </g>
            {/* Reticle ring */}
            <circle r={micro.r} fill="none" stroke={INK} strokeOpacity={0.85} strokeWidth={1.4} pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - microP} transform="rotate(-90)" />
            <circle r={micro.r + 12 * u} fill="none" stroke={INK} strokeOpacity={0.25 * microP} strokeWidth={1} />
            {Array.from({length: 72}, (_, i) => {
              const a = (i / 72) * Math.PI * 2;
              const r0 = micro.r + 12 * u;
              const r1 = r0 + (i % 6 === 0 ? 10 : 5) * u;
              return (
                <line
                  key={i}
                  x1={Math.cos(a) * r0}
                  y1={Math.sin(a) * r0}
                  x2={Math.cos(a) * r1}
                  y2={Math.sin(a) * r1}
                  stroke={INK}
                  strokeOpacity={0.35 * smoothstep(i / 72 - 0.05, i / 72, microP)}
                  strokeWidth={1}
                />
              );
            })}
            <text
              x={0}
              y={micro.r + 52 * u}
              textAnchor="middle"
              fill={INK}
              fillOpacity={0.55 * progress(f, 60, 20)}
              style={{font: `${monoSize}px "PS Mono"`, letterSpacing: '0.14em'}}
            >
              LEAF EPIDERMIS
            </text>
          </g>

          {/* F1 cross diagram */}
          <g transform={`translate(${cross.x} ${cross.y})`} opacity={0.9}>
            {(() => {
              const s = u * (portrait ? 0.9 : 1);
              const p1 = pt(-80 * s, -46 * s);
              const p2 = pt(80 * s, -46 * s);
              const m = pt(0, -46 * s);
              const f1 = pt(0, 46 * s);
              const labelStyle = {font: `${monoSize}px "PS Mono"`, letterSpacing: '0.12em'};
              return (
                <>
                  <Draw d={linePath([pt(p1.x + 9 * s, p1.y), pt(p2.x - 9 * s, p2.y)])} p={crossP} width={1} color={GOLD} />
                  <Draw d={linePath([m, pt(f1.x, f1.y - 10 * s)])} p={progress(f, 66, 24)} width={1} color={GOLD} />
                  <circle cx={p1.x} cy={p1.y} r={8 * s} fill="none" stroke={INK} strokeWidth={1.2} opacity={crossP} />
                  <circle cx={p2.x} cy={p2.y} r={8 * s} fill="none" stroke={INK} strokeWidth={1.2} opacity={crossP} />
                  <circle cx={f1.x} cy={f1.y} r={10 * s} fill={GOLD} opacity={progress(f, 80, 14)} />
                  <text x={m.x} y={m.y - 14 * s} textAnchor="middle" fill={GOLD} opacity={crossP} style={{...labelStyle, font: `${monoSize * 1.4}px "PS Mono"`}}>
                    ×
                  </text>
                  <text x={p1.x} y={p1.y - 22 * s} textAnchor="middle" fill={INK} fillOpacity={0.7 * crossP} style={labelStyle}>
                    P1
                  </text>
                  <text x={p2.x} y={p2.y - 22 * s} textAnchor="middle" fill={INK} fillOpacity={0.7 * crossP} style={labelStyle}>
                    P2
                  </text>
                  <text x={f1.x + 22 * s} y={f1.y + 5 * s} fill={GOLD} opacity={progress(f, 82, 14)} style={labelStyle}>
                    F1
                  </text>
                </>
              );
            })()}
          </g>
        </g>
      </svg>

      {/* Copy */}
      <AbsoluteFill
        style={{
          justifyContent: portrait ? 'flex-end' : 'center',
          alignItems: portrait ? 'center' : 'flex-start',
          paddingLeft: marginX,
          paddingRight: marginX,
          paddingBottom: portrait ? safeBottom : 0,
          paddingTop: portrait ? 0 : 160 * u,
        }}
      >
        <div style={{display: 'flex', flexDirection: 'column', gap: 10 * u, alignItems: portrait ? 'center' : 'flex-start'}}>
          <AnimatedText
            text={copy.research.location}
            start={24}
            exit={116}
            variant="mono"
            mode="fade"
            size={monoSize}
            align={portrait ? 'center' : 'left'}
            style={{marginBottom: 14 * u}}
          />
          {copy.research.headlineParts.map((part, i) => (
            <AnimatedText
              key={part}
              text={part}
              start={2 + i * 16}
              exit={112 + i * 2}
              size={headlineSize * (portrait ? 1 : 1.02)}
              align={portrait ? 'center' : 'left'}
              style={{lineHeight: 1.02, color: i === 0 ? palette.cream : 'rgba(244,239,227,0.92)'}}
            />
          ))}
          <AnimatedText
            text={copy.research.support}
            start={62}
            exit={116}
            variant="support"
            mode="fade"
            size={supportSize}
            align={portrait ? 'center' : 'left'}
            style={{marginTop: 22 * u}}
          />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
