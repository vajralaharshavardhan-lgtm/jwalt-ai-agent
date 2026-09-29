/**
 * Font loading. Files live in public/fonts/ (SIL Open Font License, see the
 * LICENSE-*.txt files next to them).
 *
 * PROVISIONAL: the website's own typefaces could not be inspected (see
 * brand.ts). To switch fonts, drop the .woff2 files into public/fonts/, point
 * the entries below at them, and update the family names in typography.ts.
 */
import {loadFont} from '@remotion/fonts';
import {staticFile} from 'remotion';

let loaded = false;

export const loadBrandFonts = () => {
  if (loaded) {
    return;
  }
  loaded = true;
  loadFont({
    family: 'PS Display',
    url: staticFile('fonts/Fraunces-Variable.woff2'),
    weight: '100 900',
    style: 'normal',
  });
  loadFont({
    family: 'PS Display',
    url: staticFile('fonts/Fraunces-Variable-Italic.woff2'),
    weight: '100 900',
    style: 'italic',
  });
  loadFont({
    family: 'PS Sans',
    url: staticFile('fonts/Inter-Variable.woff2'),
    weight: '100 900',
  });
  loadFont({
    family: 'PS Mono',
    url: staticFile('fonts/IBMPlexMono-Regular.woff2'),
    weight: '400',
  });
};
