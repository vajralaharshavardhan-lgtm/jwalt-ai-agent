import React from 'react';
import {Img} from 'remotion';
import {getSlot} from '../assets/useSlot';
import {palette} from '../styles/brand';
import {textStyles} from '../styles/typography';
import {ease, progress} from '../utils/easing';

export type LogoRevealProps = {
  /** Scene-local frame. */
  frame: number;
  wordmark: string;
  tagline: string;
  location: string;
  u: number;
  portrait: boolean;
  /** Frame the hairline starts drawing. */
  start?: number;
};

/**
 * End-card lockup, born from a single point of light:
 * point → golden hairline → wordmark rises out of the line (mask) with a
 * light sheen → tagline descends from the line → location.
 *
 * If public/assets/logo.(svg|png|webp) exists it is revealed above the
 * wordmark. No logo symbol is invented when it is absent.
 */
export const LogoReveal: React.FC<LogoRevealProps> = ({frame: f, wordmark, tagline, location, u, portrait, start = 14}) => {
  const logo = getSlot('logo');
  const line = progress(f, start, 24, ease.cinematic);
  const rise = progress(f, start + 12, 28, ease.out);
  const track = progress(f, start + 12, 44, ease.out);
  const descend = progress(f, start + 30, 24, ease.out);
  const loc = progress(f, start + 44, 20, ease.out);
  const sheen = progress(f, start + 40, 40, ease.inOut);
  const logoIn = progress(f, start + 26, 30, ease.out);

  const wordSize = (portrait ? 64 : 78) * u;
  const lineW = (portrait ? 620 : 700) * u;
  const gap = 30 * u;

  return (
    <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
      {logo ? (
        <div
          style={{
            height: (portrait ? 170 : 150) * u,
            marginBottom: 34 * u,
            opacity: logoIn,
            filter: `blur(${(1 - logoIn) * 12}px)`,
            transform: `translateY(${(1 - logoIn) * 14 * u}px)`,
          }}
        >
          <Img src={logo.src} style={{height: '100%', width: 'auto', objectFit: 'contain'}} />
        </div>
      ) : null}

      {/* Wordmark rises out of the line */}
      <div style={{overflow: 'hidden', paddingBottom: 4 * u}}>
        <div
          style={{
            ...textStyles.headline,
            fontSize: wordSize,
            fontWeight: 300,
            letterSpacing: `${0.34 + (1 - track) * 0.3}em`,
            marginRight: `-${0.34 + (1 - track) * 0.3}em`,
            lineHeight: 1.15,
            whiteSpace: 'nowrap',
            transform: `translateY(${(1 - rise) * 105}%)`,
            backgroundImage: `linear-gradient(100deg, ${palette.cream} 0%, ${palette.cream} ${sheen * 130 - 20}%, #FFF9EC ${sheen * 130 - 10}%, ${palette.cream} ${sheen * 130}%, ${palette.cream} 100%)`,
            WebkitBackgroundClip: 'text',
            backgroundClip: 'text',
            color: 'transparent',
          }}
        >
          {wordmark}
        </div>
      </div>

      {/* The hairline */}
      <div
        style={{
          width: lineW * line,
          height: Math.max(1, 1.5 * u),
          marginTop: gap * 0.6,
          marginBottom: gap * 0.9,
          background: `linear-gradient(90deg, rgba(201,165,107,0) 0%, ${palette.husk} 18%, ${palette.huskLight} 50%, ${palette.husk} 82%, rgba(201,165,107,0) 100%)`,
          boxShadow: `0 0 ${18 * u}px rgba(246,196,124,${0.55 * (1 - rise * 0.6)})`,
        }}
      />

      {/* Tagline descends from the line */}
      <div style={{overflow: 'hidden', paddingTop: 2 * u, paddingBottom: 8 * u}}>
        <div
          style={{
            ...textStyles.headlineItalic,
            fontSize: (portrait ? 44 : 46) * u,
            transform: `translateY(${(1 - descend) * -110}%)`,
            opacity: descend,
            textAlign: 'center',
            whiteSpace: portrait ? 'normal' : 'nowrap',
            maxWidth: portrait ? 860 * u : undefined,
          }}
        >
          {tagline}
        </div>
      </div>

      <div
        style={{
          ...textStyles.caps,
          fontSize: (portrait ? 20 : 17) * u,
          color: palette.husk,
          marginTop: 28 * u,
          opacity: loc,
          letterSpacing: `${0.42 + (1 - loc) * 0.2}em`,
          marginRight: '-0.42em',
          filter: `blur(${(1 - loc) * 5}px)`,
        }}
      >
        {location}
      </div>
    </div>
  );
};
