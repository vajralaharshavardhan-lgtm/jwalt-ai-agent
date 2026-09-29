import React, {createContext, useContext} from 'react';
import {AbsoluteFill, Sequence, useCurrentFrame} from 'remotion';
import {SCENES, type SceneId} from './timeline';

type SceneCtx = {id: SceneId; pre: number; duration: number};
const Ctx = createContext<SceneCtx | null>(null);

/**
 * Places a scene on the master timeline (see timeline.ts) and gives its
 * children a scene-local clock via useSceneFrame().
 */
export const ScenePlacement: React.FC<{id: SceneId; children: React.ReactNode}> = ({id, children}) => {
  const t = SCENES[id];
  return (
    <Sequence from={t.from - t.pre} durationInFrames={t.duration + t.pre} name={t.label} layout="none">
      <Ctx.Provider value={{id, pre: t.pre, duration: t.duration}}>
        <AbsoluteFill>{children}</AbsoluteFill>
      </Ctx.Provider>
    </Sequence>
  );
};

/** Frame relative to the scene's nominal start (negative during the pre-roll). */
export const useSceneFrame = () => {
  const frame = useCurrentFrame();
  const ctx = useContext(Ctx);
  return ctx ? frame - ctx.pre : frame;
};

export const useSceneInfo = () => {
  const ctx = useContext(Ctx);
  return ctx ?? {id: 'openingSeed' as SceneId, pre: 0, duration: 0};
};

/**
 * Standalone wrapper used by the per-scene preview compositions: renders a
 * scene with its real `pre` so previews match the film exactly.
 */
export const StandaloneScene: React.FC<{id: SceneId; children: React.ReactNode}> = ({id, children}) => {
  const t = SCENES[id];
  return (
    <Ctx.Provider value={{id, pre: t.pre, duration: t.duration}}>
      <AbsoluteFill>{children}</AbsoluteFill>
    </Ctx.Provider>
  );
};
