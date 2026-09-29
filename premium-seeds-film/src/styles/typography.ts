import type {CSSProperties} from 'react';
import {roles} from './brand';

export const fontFamilies = {
  display: '"PS Display", Georgia, serif',
  sans: '"PS Sans", "Helvetica Neue", Arial, sans-serif',
  mono: '"PS Mono", "SFMono-Regular", Menlo, monospace',
};

/**
 * Text styles. Sizes are in px at the 1080-px short edge and are multiplied by
 * the layout unit `u` (see utils/layout.ts) so 16:9, 9:16 and 4:5 all scale.
 */
export const textStyles = {
  /** Large editorial headline: one sentence per scene. */
  headline: {
    fontFamily: fontFamilies.display,
    fontWeight: 300,
    fontVariationSettings: '"opsz" 144, "SOFT" 40, "WONK" 0',
    letterSpacing: '-0.012em',
    lineHeight: 1.08,
    textWrap: 'balance',
    color: roles.textPrimary,
  },
  /** Serif italic for the brand line. */
  headlineItalic: {
    fontFamily: fontFamilies.display,
    fontStyle: 'italic',
    fontWeight: 300,
    fontVariationSettings: '"opsz" 144, "SOFT" 60, "WONK" 0',
    letterSpacing: '-0.005em',
    lineHeight: 1.12,
    textWrap: 'balance',
    color: roles.textPrimary,
  },
  /** Small supporting line under a headline. */
  support: {
    fontFamily: fontFamilies.sans,
    fontWeight: 400,
    letterSpacing: '0.01em',
    lineHeight: 1.35,
    color: roles.textSecondary,
  },
  /** Tracked capitals: eyebrows, crop names, wordmark. */
  caps: {
    fontFamily: fontFamilies.sans,
    fontWeight: 500,
    letterSpacing: '0.32em',
    textTransform: 'uppercase',
    color: roles.textPrimary,
  },
  /** Scientific micro-annotation. */
  mono: {
    fontFamily: fontFamilies.mono,
    fontWeight: 400,
    letterSpacing: '0.14em',
    textTransform: 'uppercase',
    color: roles.textMuted,
  },
} satisfies Record<string, CSSProperties>;
