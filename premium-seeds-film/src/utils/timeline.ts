/**
 * Master timeline. 30 fps, 45 s = 1350 frames.
 *
 * `from`/`duration` are the scene's nominal slot in the storyboard.
 * `pre` is how many frames the scene starts early, drawn ON TOP of the
 * previous scene, so it can dissolve / match-cut in. Inside a scene,
 * useSceneFrame() returns 0 at `from` and negative values during `pre`.
 */
export const FPS = 30;
export const sec = (s: number) => Math.round(s * FPS);

export type SceneId =
  | 'openingSeed'
  | 'germination'
  | 'research'
  | 'field'
  | 'crops'
  | 'topGun'
  | 'harvest'
  | 'returnToSeed'
  | 'finalReveal';

export type SceneTiming = {
  from: number;
  duration: number;
  pre: number;
  label: string;
};

export const SCENES: Record<SceneId, SceneTiming> = {
  openingSeed: {from: 0, duration: 120, pre: 0, label: '01 Opening seed'},
  germination: {from: 120, duration: 120, pre: 0, label: '02 Germination'},
  research: {from: 240, duration: 150, pre: 20, label: '03 Research'},
  field: {from: 390, duration: 150, pre: 16, label: '04 Field validation'},
  crops: {from: 540, duration: 180, pre: 14, label: '05 Crop portfolio'},
  topGun: {from: 720, duration: 150, pre: 14, label: '06 Top Gun F1'},
  harvest: {from: 870, duration: 180, pre: 18, label: '07 Farmer & harvest'},
  returnToSeed: {from: 1050, duration: 150, pre: 16, label: '08 Return to seed'},
  finalReveal: {from: 1200, duration: 150, pre: 0, label: '09 Final reveal'},
};

export const SCENE_ORDER: SceneId[] = [
  'openingSeed',
  'germination',
  'research',
  'field',
  'crops',
  'topGun',
  'harvest',
  'returnToSeed',
  'finalReveal',
];

export const TOTAL_FRAMES = 1350;
