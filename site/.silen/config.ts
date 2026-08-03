import { defineConfig } from '@aicode-nexus/silen'

const zhNav = [
  { text: '快速开始', link: '/guide/' },
  { text: '知识网络', link: '/knowledge-network/' },
  { text: '能力', link: '/features/' },
  { text: '安全', link: '/security/' },
  { text: '参考', link: '/reference/' },
]

const enNav = [
  { text: 'Guide', link: '/en/guide/' },
  { text: 'Knowledge Network', link: '/en/knowledge-network/' },
  { text: 'Features', link: '/en/features/' },
  { text: 'Security', link: '/en/security/' },
  { text: 'Reference', link: '/en/reference/' },
]

const zhSidebar = [
  {
    text: '开始使用',
    items: [
      { text: '五分钟上手', link: '/guide/' },
      { text: '知识网络', link: '/knowledge-network/' },
    ],
  },
  {
    text: '产品手册',
    items: [
      { text: '核心能力', link: '/features/' },
      { text: '安全边界', link: '/security/' },
      { text: '命令与配置', link: '/reference/' },
    ],
  },
]

const enSidebar = [
  {
    text: 'Get started',
    items: [
      { text: 'Five-minute guide', link: '/en/guide/' },
      { text: 'Knowledge network', link: '/en/knowledge-network/' },
    ],
  },
  {
    text: 'Product manual',
    items: [
      { text: 'Core features', link: '/en/features/' },
      { text: 'Security boundaries', link: '/en/security/' },
      { text: 'CLI and configuration', link: '/en/reference/' },
    ],
  },
]

export default defineConfig({
  title: 'Mini-Wiki',
  description: 'A source-traceable project knowledge network for people and AI.',
  lang: 'zh-CN',
  base: '/mini-wiki/',
  siteUrl: 'https://trsoliu.github.io',
  onBrokenLinks: 'error',
  themeConfig: {
    logo: { src: '/logo.svg', alt: 'Mini-Wiki' },
    search: true,
    nav: zhNav,
    sidebar: zhSidebar,
    socialLinks: [
      {
        icon: 'github',
        link: 'https://github.com/trsoliu/mini-wiki',
        ariaLabel: 'Mini-Wiki on GitHub',
      },
    ],
    locales: [
      {
        lang: 'zh-CN',
        label: '简体中文',
        root: '/',
        link: '/',
        nav: zhNav,
        sidebar: zhSidebar,
      },
      {
        lang: 'en',
        label: 'English',
        root: '/en/',
        link: '/en/',
        nav: enNav,
        sidebar: enSidebar,
      },
    ],
  },
  ai: {
    llmsTxt: true,
    llmsFullTxt: true,
    markdownRoutes: true,
    index: true,
    contract: {
      enabled: true,
      instructions: '.silen/ai-public.md',
    },
  },
})
