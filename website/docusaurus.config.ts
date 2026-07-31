import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'Cyberfox Agent',
  tagline: 'The self-improving AI agent',
  favicon: 'img/favicon.ico',

  url: 'http://localhost:3000',
  baseUrl: '/',

  organizationName: 'Sarthak5-t',
  projectName: 'cyberfox-agent',

  onBrokenLinks: 'warn',

  markdown: {
    mermaid: true,
    hooks: {
      onBrokenMarkdownLinks: 'warn',
    },
  },

  i18n: {
    defaultLocale: 'en',
    locales: ['en', 'zh-Hans'],
    localeConfigs: {
      en: {
        label: 'English',
      },
      'zh-Hans': {
        label: '简体中文',
        htmlLang: 'zh-Hans',
      },
    },
  },

  themes: [
    '@docusaurus/theme-mermaid',
  ],

  presets: [
    [
      'classic',
      {
        docs: false,
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    image: 'img/cyberfox-agent-banner.png',
    colorMode: {
      defaultMode: 'dark',
      respectPrefersColorScheme: true,
    },
    docs: {
      sidebar: {
        hideable: true,
        autoCollapseCategories: true,
      },
    },
    navbar: {
      title: 'Cyberfox Agent',
      logo: {
        alt: 'Cyberfox Agent',
        src: 'img/logo.png',
      },
      items: [
        {
          to: '/skills',
          label: 'Skills',
          position: 'left',
        },
        {
          href: 'https://github.com/Sarthak5-t/Cyberfox',
          label: 'Download',
          position: 'left',
        },
        {
          type: 'localeDropdown',
          position: 'right',
        },
        {
          href: 'https://github.com/Sarthak5-t/Cyberfox',
          label: 'Home',
          position: 'right',
        },
        {
          href: 'https://github.com/Sarthak5-t/Cyberfox',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Community',
          items: [
            { label: 'GitHub Issues', href: 'https://github.com/Sarthak5-t/Cyberfox/issues' },
            { label: 'Skills Hub', href: 'https://agentskills.io' },
          ],
        },
        {
          title: 'More',
          items: [
            { label: 'Desktop Download', href: 'https://github.com/Sarthak5-t/Cyberfox' },
            { label: 'GitHub', href: 'https://github.com/Sarthak5-t/Cyberfox' },
          ],
        },
      ],
      copyright: `Built by Cyberfox · MIT License · ${new Date().getFullYear()}`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash', 'yaml', 'json', 'python', 'toml'],
    },
    mermaid: {
      theme: {light: 'neutral', dark: 'dark'},
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
