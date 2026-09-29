/**
 * ALL ON-SCREEN TEXT lives here. Edit this file to change wording.
 *
 * Every factual statement below comes from the Premium Seeds website as quoted
 * in the creative brief. Do not add claims (awards, certifications, farmer
 * counts, acreage, yields...) that the website does not make.
 *
 * Set a string to '' to hide that line.
 */
export const copy = {
  openingSeed: {
    headline: 'Every harvest begins with a seed.',
  },
  germination: {
    headline: 'But better seeds begin with better breeding.',
  },
  research: {
    /** Revealed one after another, read as one sentence. */
    headlineParts: ['Vegetable genetics.', 'Research.', 'Field validation.'],
    support: 'Designed for Indian growing conditions.',
    /** Micro label on the research plate. Verify exact wording on the website. */
    location: 'R&D · Agri Innovation Centre, GKVK · UAS Bengaluru',
  },
  field: {
    headline: 'From research to the field.',
    support: 'Validated across growing conditions.',
  },
  crops: {
    headline: '25+ vegetable crops',
    support: 'Built around real farming needs.',
    /** Montage order (must match the CROPS list in visuals/crops.ts). */
    names: ['Chilli', 'Cucumber', 'Watermelon', 'Bitter gourd', 'Bottle gourd', 'Ridge gourd', 'Tomato', 'Okra'],
  },
  topGun: {
    eyebrow: 'Featured variety',
    name: 'TOP GUN F1',
    descriptor: 'Chilli · F1 Hybrid',
    specs: [
      {value: '55,000 SHU', label: 'Pungency'},
      {value: '74 ASTA', label: 'Colour value'},
    ],
  },
  harvest: {
    headline: 'Healthy crops.',
    support: 'Better possibilities for farmers.',
  },
  returnToSeed: {
    /** Optional quiet line over the floating seed. Empty by default: the image carries it. */
    line: '',
  },
  finalReveal: {
    wordmark: 'PREMIUM SEEDS',
    tagline: 'Better seed starts with the breeder.',
    location: 'Bengaluru · India',
  },
} as const;
