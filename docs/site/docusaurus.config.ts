import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)

const ORG = 'databricks-solutions';
const REPO = 'databricks-genie-workbench';

const config: Config = {
  title: 'Genie Workbench',
  tagline: 'Create, score, and optimize Databricks Genie Spaces',
  favicon: 'img/favicon.svg',

  // Production URL for GitHub Pages: https://databricks-solutions.github.io/databricks-genie-workbench/
  url: `https://${ORG}.github.io`,
  baseUrl: `/${REPO}/`,
  trailingSlash: true,

  organizationName: ORG,
  projectName: REPO,

  onBrokenLinks: 'throw',

  markdown: {
    mermaid: true,
    hooks: {
      onBrokenMarkdownLinks: 'warn',
    },
  },
  themes: ['@docusaurus/theme-mermaid'],

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          routeBasePath: '/docs',
          editUrl: `https://github.com/${ORG}/${REPO}/tree/main/docs/site/`,
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  plugins: [
    // Tailwind CSS integration via PostCSS, matching the Lakebridge docs setup.
    async function tailwindPlugin() {
      return {
        name: 'docusaurus-tailwindcss',
        configurePostCss(postcssOptions) {
          postcssOptions.plugins.push(
            require('tailwindcss'),
            require('autoprefixer'),
          );
          return postcssOptions;
        },
      };
    },
    // Full-text search (no external service required).
    require.resolve('docusaurus-lunr-search'),
    // Click-to-zoom on doc images.
    [
      'docusaurus-plugin-image-zoom',
      {
        selector: '.markdown img',
        background: {light: '#F8FAFC', dark: '#1b3139'},
      },
    ],
    // Generate llms.txt (+ per-page markdown) for LLM consumption.
    [
      '@signalwire/docusaurus-plugin-llms-txt',
      {
        siteTitle: 'Genie Workbench',
        siteDescription:
          'Developer tool for creating, scoring, and optimizing Databricks Genie Spaces.',
      },
    ],
  ],

  themeConfig: {
    image: 'img/social-card.png',
    colorMode: {
      // Dark-default regardless of OS preference, matching the Lakebridge docs.
      // Visitors can still toggle; the choice persists in localStorage.
      defaultMode: 'dark',
      respectPrefersColorScheme: false,
    },
    mermaid: {
      theme: {light: 'neutral', dark: 'dark'},
    },
    navbar: {
      title: 'Genie Workbench',
      logo: {
        alt: 'Genie Workbench',
        src: 'img/logo.svg',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'docsSidebar',
          position: 'left',
          label: 'Documentation',
        },
        {
          to: '/docs/getting-started/introduction',
          label: 'Get Started',
          position: 'left',
        },
        {
          href: `https://github.com/${ORG}/${REPO}`,
          position: 'right',
          className: 'header-github-link',
          'aria-label': 'GitHub repository',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Getting Started',
          items: [
            {label: 'Introduction', to: '/docs/getting-started/introduction'},
            {label: 'Architecture Overview', to: '/docs/getting-started/architecture-overview'},
            {label: 'Deployment Guide', to: '/docs/getting-started/deployment-guide'},
          ],
        },
        {
          title: 'Features',
          items: [
            {label: 'Create Agent', to: '/docs/features/create-agent'},
            {label: 'IQ Scanner', to: '/docs/features/iq-scanner'},
            {label: 'Fix Agent', to: '/docs/features/fix-agent'},
            {label: 'Auto-Optimize', to: '/docs/features/auto-optimize'},
          ],
        },
        {
          title: 'Reference',
          items: [
            {label: 'API Reference', to: '/docs/reference/api'},
            {label: 'Environment Variables', to: '/docs/reference/environment-variables'},
            {label: 'Troubleshooting', to: '/docs/reference/troubleshooting'},
          ],
        },
        {
          title: 'More',
          items: [
            {label: 'GitHub', href: `https://github.com/${ORG}/${REPO}`},
            {label: 'Databricks Genie', href: 'https://docs.databricks.com/aws/en/genie/'},
          ],
        },
      ],
      copyright: `© Databricks ${new Date().getFullYear()}. Provided by Databricks Solutions.`,
    },
    prism: {
      theme: prismThemes.oneLight,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash', 'python', 'sql', 'json'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
