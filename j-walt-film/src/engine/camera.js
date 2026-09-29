// Camera system: places a photograph inside an aperture (a screen-space
// rectangle) the way a cinematographer frames a still.
//
//   cam = { zoom, cx, cy, px, py }
//     zoom   1 = the smallest scale that covers the aperture ("cover")
//     cx,cy  image-space focus point (0..1) held at the aperture centre
//     px,py  extra screen-space offset (window parallax, drift)
//
// The camera never rotates and never scales non-uniformly: architecture is
// never bent, stretched or tilted. The returned transform is also used to
// draw overlays (construction lines) in image space, so they stay registered
// to the photograph under any move.

export function frame(img, rect, cam = {}) {
  const zoom = cam.zoom ?? 1;
  const cover = Math.max(rect.w / img.w, rect.h / img.h);
  const s = cover * zoom;
  let ox = rect.x + rect.w / 2 - (cam.cx ?? 0.5) * img.w * s + (cam.px ?? 0);
  let oy = rect.y + rect.h / 2 - (cam.cy ?? 0.5) * img.h * s + (cam.py ?? 0);
  // the photograph must always cover its aperture -- no empty edges
  ox = Math.min(rect.x, Math.max(rect.x + rect.w - img.w * s, ox));
  oy = Math.min(rect.y, Math.max(rect.y + rect.h - img.h * s, oy));
  return {
    s, ox, oy,
    upscale: s / (img.density ?? 1), // >1 means source pixels are being enlarged
    pt: (x, y) => [ox + x * s, oy + y * s],
  };
}

// Draw a photograph through its aperture. `clip` may be narrower than the
// aperture (masked reveals); the framing is always computed on the full
// aperture so a reveal never moves the picture.
export function drawPhoto(ctx, img, rect, cam, { clip = rect, opacity = 1, stats } = {}) {
  const T = frame(img, rect, cam);
  if (clip.w <= 0 || clip.h <= 0 || opacity <= 0) return T;
  ctx.save();
  ctx.beginPath();
  ctx.rect(clip.x, clip.y, clip.w, clip.h);
  ctx.clip();
  ctx.globalAlpha = opacity;
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';
  // a view is a safe sub-rectangle of the source photo (sx, sy, w, h); the
  // camera can never show anything outside it (boxes, stray logo fragments)
  ctx.drawImage(img.el, img.sx ?? 0, img.sy ?? 0, img.w, img.h, T.ox, T.oy, img.w * T.s, img.h * T.s);
  ctx.restore();
  if (stats) stats.push({ id: img.id, upscale: +T.upscale.toFixed(3) });
  return T;
}
