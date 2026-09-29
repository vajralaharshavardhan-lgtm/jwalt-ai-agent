import {useVideoConfig} from 'remotion';

/**
 * Orientation-aware layout. Every size in the film is expressed in `u`, one
 * pixel at a 1080-px short edge, so the same scene code renders 16:9 (1920×1080),
 * 9:16 (1080×1920) and 4:5 (1080×1350) without per-format forks.
 */
export const useLayout = () => {
  const {width, height} = useVideoConfig();
  const portrait = height > width * 1.05;
  const short = Math.min(width, height);
  const u = short / 1080;
  return {
    width,
    height,
    portrait,
    u,
    cx: width / 2,
    cy: height / 2,
    /** Horizontal text margin. */
    marginX: (portrait ? 84 : 150) * u,
    /** Keep text clear of platform UI (Reels/Shorts overlays top and bottom). */
    safeTop: (portrait ? 240 : 96) * u,
    safeBottom: (portrait ? 360 : 104) * u,
    headlineSize: (portrait ? 74 : 70) * u,
    supportSize: (portrait ? 30 : 26) * u,
    capsSize: (portrait ? 22 : 18) * u,
    monoSize: (portrait ? 17 : 14) * u,
  };
};

export type Layout = ReturnType<typeof useLayout>;
