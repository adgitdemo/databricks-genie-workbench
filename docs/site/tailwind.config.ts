import type {Config} from 'tailwindcss';

// Tailwind is layered on top of Docusaurus's Infima styles.
// `preflight` is disabled so Tailwind's CSS reset does not clobber
// Docusaurus's own heading/typography defaults.
const config: Config = {
  corePlugins: {
    preflight: false,
  },
  darkMode: ['class', '[data-theme="dark"]'],
  content: [
    './src/**/*.{js,jsx,ts,tsx,md,mdx}',
    './docs/**/*.{md,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Databricks brand palette
        'db-navy': '#1b3139',
        'db-blue': '#2272b4',
        'db-blue-light': '#4299e0',
        'db-red': '#eb1600',
        'db-mist': '#F8FAFC',
      },
      fontFamily: {
        sans: ['"DM Sans"', 'system-ui', 'sans-serif'],
        mono: ['"DM Mono"', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
};

export default config;
