import {staticFile} from 'remotion';
import {AVAILABLE_ASSETS, GENERATED_AUDIO} from './available.generated';
import slotsJson from './slots.json';

export type SlotId = (typeof slotsJson.slots)[number]['id'];
export type SlotAsset = {src: string; kind: 'image' | 'video' | 'audio'};

export const SLOTS = slotsJson.slots;

/** The real asset for a slot if one was dropped into public/assets/, else null. */
export const getSlot = (id: SlotId): SlotAsset | null => {
  const a = AVAILABLE_ASSETS[id];
  return a ? {src: staticFile(a.file), kind: a.kind} : null;
};

export const generatedAudio = (name: 'music' | 'sfx') =>
  GENERATED_AUDIO[name] ? staticFile(`audio/generated/${name}.wav`) : null;
