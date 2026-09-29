import React from 'react';
import {AbsoluteFill, interpolateColors} from 'remotion';
import {AnimatedText} from '../components/AnimatedText';
import {Particles} from '../components/Atmosphere';
import {Seed} from '../components/Seed';
import {copy} from '../content/copy';
import {ease, lerp, progress, tween} from '../utils/easing';
import {type Pt, add, linePath, pt, rand, ribbon, rotate, smoothPath, tangentAt, trimPolyline, perp, scale} from '../utils/geometry';
import {useLayout} from '../utils/layout';
import {useSceneFrame} from '../utils/scene';
import {OPENING_SEED_END, seedBaseSize, seedCenterY} from './OpeningSeed';
import {GERM_CAMERA_END, SEED_REST_ROT, cotyledonRotations, cotyledonShape, seedTip, seedlingGeometry, seedlingState} from '../visuals/seedling';

/** Camera for Germination at scene-local frame f (shared with Research's opening). */
export const germCamera = (f: number) => {
  const pull = progress(f, 4, 70, ease.cinematic);
  const settle = progress(f, 60, 60, ease.gentle);
  return {
    scale: lerp(OPENING_SEED_END.scale, 0.44, pull) + (GERM_CAMERA_END.scale - 0.44) * settle,
    offsetY: lerp(0, 0.08, pull) + (GERM_CAMERA_END.offsetY - 0.08) * settle,
    seedRot: lerp(OPENING_SEED_END.rotate, SEED_REST_ROT, progress(f, 2, 60, ease.inOut)),
  };
};

/** Where a world point lands on screen. */
export const worldToScreen = (p: Pt, cam: {scale: number; offsetY: number}, cx: number, sy: number, height: number): Pt =>
  pt(cx + p.x * cam.scale, sy + cam.offsetY * height + p.y * cam.scale);

/**
 * SCENE 02 · 0:04–0:08
 * Match cut from the cracked seed. Light floods out and reveals the soil
 * around it (a rhizotron-style cross-section) as the camera pulls back:
 * the radicle pushes down, root hairs feather out, the hypocotyl hooks up
 * through the soil and the cotyledons open into the light.
 */
export const Germination: React.FC = () => {
  const f = useSceneFrame();
  const {portrait, u, cx, width, height, headlineSize, marginX, safeBottom} = useLayout();
  const size = seedBaseSize(portrait, u);
  const sy = seedCenterY(portrait, height);
  const cam = germCamera(f);
  const geo = seedlingGeometry(size);
  const st = seedlingState(f);
  const {k} = geo;

  const soilIn = tween(f, [0, 34], [0, 1], ease.out);
  const flash = tween(f, [0, 26], [1, 0], ease.out);
  const glow = tween(f, [0, 40], [1, 0.15], ease.out);

  // Visible world bounds (+ margin) so filters only cost what is on screen.
  const toWorld = (sx: number, syy: number) => pt((sx - cx) / cam.scale, (syy - sy - cam.offsetY * height) / cam.scale);
  const tl = toWorld(-40, -40);
  const br = toWorld(width + 40, height + 40);
  const soilTop = Math.max(tl.y, geo.surfaceY - 60 * k);

  // Root and shoot at current growth.
  const root = trimPolyline(geo.root, st.root);
  const shoot = trimPolyline(geo.shoot, st.shoot);
  const rootOutline = root.length > 2 ? ribbon(root, (s) => lerp(21, 4, Math.pow(s, 0.7)) * k * lerp(0.6, 1, st.root)) : null;
  const shootOutline = shoot.length > 2 ? ribbon(shoot, (s) => lerp(17, 14, s) * k) : null;
  const shootTip = shoot[shoot.length - 1];
  const shootDir = shoot.length > 1 ? tangentAt(shoot, shoot.length - 1) : pt(0, -1);
  const [rotL, rotR] = cotyledonRotations(st.open);
  const cotLen = lerp(140, 330, st.open) * k;
  const cot = cotyledonShape(cotLen);
  const cotColor = interpolateColors(st.open, [0, 1], ['#E4DDA4', '#6FA348']);
  const shootColor = interpolateColors(st.open, [0, 1], ['#EDE6BE', '#B9CF7F']);

  // Root hairs along the grown part.
  const rootLen = geo.root.length;
  const hairs = geo.hairs
    .map((h, i) => {
      const idx = Math.floor(h.at * (rootLen - 1));
      const needed = h.at + 0.1;
      if (st.root < needed) {
        return null;
      }
      const grow = Math.min(1, (st.root - needed) / 0.18) * st.hairs;
      const base = geo.root[idx];
      const tan = tangentAt(geo.root, idx);
      const dir = rotate(scale(perp(tan), h.side), (h.angle - 0.9) * 0.8 * h.side);
      const end = add(base, scale(dir, h.length * grow));
      return <path key={i} d={linePath([base, end])} stroke="#F6F0DE" strokeOpacity={0.7} strokeWidth={1.8 * k} />;
    })
    .filter(Boolean);

  // Surface line with a little irregularity.
  const surface: Pt[] = [];
  const x0 = Math.floor((tl.x - 200) / 50) * 50;
  for (let x = x0; x <= br.x + 200; x += 50) {
    const j = Math.round(x / 50);
    surface.push(pt(x, geo.surfaceY + (rand(`surf-${j}`) - 0.5) * 34 * k + (rand(`surf2-${Math.round(j / 5)}`) - 0.5) * 40 * k));
  }

  const worldTransform = `translate(${cx} ${sy + cam.offsetY * height}) scale(${cam.scale})`;
  // Flash sits on the seed tip at the seed's current angle (not its resting angle).
  const tipScreen = worldToScreen(seedTip(size, cam.seedRot), cam, cx, sy, height);

  return (
    <AbsoluteFill style={{background: '#030504'}}>
      {/* Air above the soil: dark, with light falling from above. */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 60% 55% at 50% 0%, rgba(246,196,124,${0.16 * st.open + 0.04}) 0%, rgba(20,34,24,0.25) 45%, rgba(0,0,0,0) 80%)`,
        }}
      />
      <svg width={width} height={height} style={{position: 'absolute', inset: 0}}>
        <defs>
          <filter
            id="g-soil"
            filterUnits="userSpaceOnUse"
            x={tl.x}
            y={soilTop - 60 * k}
            width={br.x - tl.x}
            height={Math.max(1, br.y - soilTop + 60 * k)}
          >
            <feTurbulence type="fractalNoise" baseFrequency="0.009" numOctaves={4} seed={4} result="clumps" />
            <feColorMatrix
              in="clumps"
              type="matrix"
              values="0.34 0 0 0 -0.02  0.24 0 0 0 -0.02  0.16 0 0 0 -0.015  0 0 0 0 1"
              result="brown"
            />
            <feTurbulence type="fractalNoise" baseFrequency="0.11" numOctaves={3} seed={9} result="grain" />
            <feDiffuseLighting in="grain" surfaceScale={5} diffuseConstant={1.1} lightingColor="#B08864" result="lit">
              <feDistantLight azimuth={235} elevation={38} />
            </feDiffuseLighting>
            <feBlend in="brown" in2="lit" mode="multiply" result="soil" />
            <feTurbulence type="fractalNoise" baseFrequency="0.35" numOctaves={1} seed={21} result="speck" />
            <feColorMatrix in="speck" type="matrix" values="0 0 0 0 0.85  0 0 0 0 0.74  0 0 0 0 0.58  0 0 0 11 -7.3" result="sand" />
            <feComposite in="sand" in2="soil" operator="over" />
          </filter>
          <linearGradient id="g-root" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="#CFC2A0" />
            <stop offset="0.5" stopColor="#FBF6E8" />
            <stop offset="1" stopColor="#BFB08A" />
          </linearGradient>
          <radialGradient id="g-pebble" cx="0.35" cy="0.3" r="0.8">
            <stop offset="0" stopColor="#8A7258" />
            <stop offset="0.5" stopColor="#4A3726" />
            <stop offset="1" stopColor="#1C130B" />
          </radialGradient>
          <linearGradient id="g-cot-light" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#E9F5B8" stopOpacity="0.65" />
            <stop offset="0.45" stopColor="#9CC46A" stopOpacity="0.15" />
            <stop offset="1" stopColor="#173012" stopOpacity="0.55" />
          </linearGradient>
          <linearGradient id="g-soil-top" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#C8996A" stopOpacity="0.45" />
            <stop offset="1" stopColor="#C8996A" stopOpacity="0" />
          </linearGradient>
          <filter id="g-rim" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation={2 * k} />
          </filter>
          <filter id="g-blur" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation={6 * k} />
          </filter>
        </defs>

        <g transform={worldTransform}>
          {/* Soil cross-section, clipped to the irregular surface line */}
          <clipPath id="g-soil-clip">
            <path d={`${smoothPath(surface)}L${br.x + 300},${br.y + 300}L${tl.x - 300},${br.y + 300}Z`} />
          </clipPath>
          <g opacity={soilIn} clipPath="url(#g-soil-clip)">
            <rect
              x={tl.x}
              y={soilTop - 60 * k}
              width={br.x - tl.x}
              height={Math.max(1, br.y - soilTop + 60 * k)}
              filter="url(#g-soil)"
            />
            {Array.from({length: 70}, (_, i) => {
              const px = lerp(-2600, 2600, rand(`peb-x-${i}`)) * k;
              const py = lerp(geo.surfaceY + 60 * k, 2600 * k, rand(`peb-y-${i}`));
              const r = lerp(10, 46, Math.pow(rand(`peb-r-${i}`), 2)) * k;
              return (
                <ellipse
                  key={i}
                  cx={px}
                  cy={py}
                  rx={r}
                  ry={r * lerp(0.55, 0.9, rand(`peb-e-${i}`))}
                  transform={`rotate(${rand(`peb-a-${i}`) * 180} ${px} ${py})`}
                  fill="url(#g-pebble)"
                  opacity={0.85}
                />
              );
            })}
            {/* Soil surface: irregular crumb line, lit from above. */}
            <rect x={tl.x} y={geo.surfaceY - 30 * k} width={br.x - tl.x} height={140 * k} fill="url(#g-soil-top)" />
            <path d={smoothPath(surface)} stroke="#B38A62" strokeOpacity={0.55} strokeWidth={2.5 / cam.scale} fill="none" />
          </g>

          {/* Root: soft translucent glow + body + hairs */}
          {rootOutline ? (
            <g>
              <path d={smoothPath(rootOutline, true)} fill="#FFF3D8" opacity={0.25} filter="url(#g-blur)" />
              <path d={smoothPath(rootOutline, true)} fill="url(#g-root)" stroke="#A89A76" strokeOpacity={0.5} strokeWidth={1.2 * k} />
              {hairs}
            </g>
          ) : null}

          {/* Shoot (hypocotyl) and cotyledons */}
          {shootOutline ? (
            <g>
              <path d={smoothPath(shootOutline, true)} fill={shootColor} stroke="#8F9A62" strokeOpacity={0.5} strokeWidth={1.2 * k} />
              {[rotL, rotR].map((r, i) => {
                const pts = cot.map((p) => rotate(p, r));
                const base = add(shootTip, scale(shootDir, 4 * k));
                const moved = pts.map((p) => add(p, base));
                const mid = [base, add(base, rotate(pt(0, cotLen * 0.92), r))];
                return (
                  <g key={i} opacity={Math.min(1, st.shoot * 3)}>
                    <path d={smoothPath(moved, true)} fill={cotColor} stroke="#2F4C1F" strokeOpacity={0.5} strokeWidth={1.4 * k} />
                    {/* Light from above: a lit upper half and a warm rim. */}
                    <path d={smoothPath(moved, true)} fill="url(#g-cot-light)" opacity={0.85 * st.open} />
                    <path d={smoothPath(moved, true)} fill="none" stroke="#FFE3A8" strokeOpacity={0.55 * st.open} strokeWidth={2.2 * k} filter="url(#g-rim)" />
                    <path d={smoothPath(mid)} stroke="#E6F0C0" strokeOpacity={0.5} strokeWidth={2 * k} fill="none" />
                  </g>
                );
              })}
            </g>
          ) : null}

          {/* Moisture beads catching light near the seed and root */}
          {Array.from({length: 16}, (_, i) => {
            const px = lerp(-700, 700, rand(`drop-x-${i}`)) * k;
            const py = lerp(-500, 1400, rand(`drop-y-${i}`)) * k;
            if (py < geo.surfaceY) {
              return null;
            }
            const r = lerp(5, 13, rand(`drop-r-${i}`)) * k;
            return (
              <g key={i} opacity={soilIn * 0.9}>
                <circle cx={px} cy={py} r={r} fill="rgba(255,255,255,0.06)" stroke="rgba(255,248,230,0.35)" strokeWidth={0.8 * k} />
                <circle cx={px - r * 0.35} cy={py - r * 0.35} r={r * 0.22} fill="#FFFDF6" opacity={0.85} />
              </g>
            );
          })}
        </g>
      </svg>

      {/* The seed coat stays where it lay (HTML layer on the same camera). */}
      <div
        style={{
          position: 'absolute',
          left: cx,
          top: sy + cam.offsetY * height,
          transform: `translate(-50%, -50%) scale(${cam.scale}) rotate(${cam.seedRot}deg)`,
        }}
      >
        <Seed
          id="s2-seed"
          size={size}
          lightX={lerp(OPENING_SEED_END.lightX, 0.3, soilIn)}
          lightY={OPENING_SEED_END.lightY}
          keyLight={lerp(1, 0.78, soilIn)}
          rimLight={lerp(0.95, 0.35, soilIn)}
          crack={1}
          glow={glow}
        />
      </div>

      {/* Pool of light around the seedling; soil falls off into darkness. */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse ${portrait ? '85% 55%' : '55% 75%'} at ${(tipScreen.x / width) * 100}% ${(tipScreen.y / height) * 100}%, rgba(0,0,0,0) 15%, rgba(3,5,4,0.62) 60%, rgba(3,5,4,0.94) 100%)`,
          opacity: soilIn,
        }}
      />
      <Particles seed="s2-motes" count={18} size={[2, 7]} drift={{x: 2, y: -4}} opacity={0.25 * soilIn} focus={0.5} />

      {/* Flash of light carried over from the crack. */}
      <AbsoluteFill
        style={{
          opacity: flash * 0.85,
          mixBlendMode: 'screen',
          background: `radial-gradient(circle at ${(tipScreen.x / width) * 100}% ${(tipScreen.y / height) * 100}%, rgba(255,236,196,0.9) 0%, rgba(246,196,124,0.35) 18%, rgba(0,0,0,0) 50%)`,
        }}
      />

      <AbsoluteFill
        style={{
          justifyContent: 'flex-end',
          alignItems: portrait ? 'center' : 'flex-start',
          paddingLeft: marginX,
          paddingRight: marginX,
          paddingBottom: portrait ? safeBottom + 40 * u : safeBottom,
        }}
      >
        <AnimatedText
          text={copy.germination.headline}
          start={14}
          exit={98}
          size={headlineSize}
          align={portrait ? 'center' : 'left'}
          maxWidth={portrait ? width - marginX * 2 : 820 * u}
          style={{textShadow: '0 2px 28px rgba(0,0,0,0.75)'}}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
