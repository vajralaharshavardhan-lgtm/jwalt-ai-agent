import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {PremiumSeedsFilm} from './PremiumSeedsFilm';
import {AVAILABLE_ASSETS} from '../assets/available.generated';
import {SLOTS} from '../assets/useSlot';
import {SCENES, SCENE_ORDER} from '../utils/timeline';
import {fontFamilies} from '../styles/typography';

// Which slots each scene can use.
const SCENE_SLOTS: Record<string, string[]> = {
  openingSeed: [],
  germination: [],
  research: ['research-breeder'],
  field: ['field-wide'],
  crops: ['crop-chilli', 'crop-cucumber', 'crop-watermelon', 'crop-bitter-gourd', 'crop-bottle-gourd', 'crop-ridge-gourd', 'crop-tomato', 'crop-okra'],
  topGun: ['topgun-product'],
  harvest: ['harvest-farmer', 'harvest-hands', 'harvest-basket'],
  returnToSeed: [],
  finalReveal: ['logo'],
};

/**
 * The film with an overlay naming the scene, its timecode, and each asset
 * slot it uses (green = supplied, amber = using the built-in fallback).
 */
export const AssetGuide: React.FC = () => {
  const frame = useCurrentFrame();
  const id = [...SCENE_ORDER].reverse().find((s) => frame >= SCENES[s].from) ?? 'openingSeed';
  const scene = SCENES[id];
  const tc = (fr: number) => `0:${String(Math.floor(fr / 30)).padStart(2, '0')}`;
  return (
    <AbsoluteFill>
      <PremiumSeedsFilm withAudio={false} />
      <AbsoluteFill style={{padding: 36, fontFamily: fontFamilies.mono, color: '#fff', fontSize: 20}}>
        <div style={{background: 'rgba(0,0,0,0.72)', padding: '14px 18px', alignSelf: 'flex-start', borderRadius: 6, lineHeight: 1.55}}>
          <div style={{fontSize: 24}}>
            {scene.label} · {tc(scene.from)}–{tc(scene.from + scene.duration)} · f{frame}
          </div>
          {SCENE_SLOTS[id].length === 0 ? (
            <div style={{opacity: 0.7}}>No asset slots (fully procedural by design)</div>
          ) : (
            SCENE_SLOTS[id].map((s) => {
              const ok = Boolean(AVAILABLE_ASSETS[s]);
              const meta = SLOTS.find((x) => x.id === s);
              return (
                <div key={s} style={{color: ok ? '#8CE99A' : '#FFC46B'}}>
                  {ok ? '● supplied ' : '○ missing  '} public/assets/{s}.{meta?.kinds[0]}
                  {ok ? '' : `  → fallback: ${meta?.fallback}`}
                </div>
              );
            })
          )}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
