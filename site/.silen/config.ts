import { defineConfig, definePlugin } from '@aicode-nexus/silen'

const isolateSsrRuntime = definePlugin(() => ({
  name: 'mini-wiki:ssr-isolation',
  vite: () => ({
    name: 'mini-wiki:ssr-isolation',
    // Prevent an ancestor workspace from injecting a second React instance into Silen SSR.
    config: () => ({ ssr: { noExternal: true } }),
  }),
}))

const releaseUrl = 'https://github.com/trsoliu/mini-wiki/releases/tag/v3.3.0'

const zhNav = [{ text: 'v3.3.0', link: releaseUrl }]

const enNav = [{ text: 'v3.3.0', link: releaseUrl }]

const zhSidebar = [
  {
    text: '开始使用',
    items: [{ text: '五分钟上手', link: '/guide/' }],
  },
  {
    text: '核心概念',
    items: [
      { text: '知识网络', link: '/knowledge-network/' },
      { text: '核心能力', link: '/features/' },
    ],
  },
  {
    text: '运维与参考',
    items: [
      { text: '安全边界', link: '/security/' },
      { text: '命令与配置', link: '/reference/' },
    ],
  },
]

const enSidebar = [
  {
    text: 'Get started',
    items: [{ text: 'Five-minute guide', link: '/en/guide/' }],
  },
  {
    text: 'Core concepts',
    items: [
      { text: 'Knowledge network', link: '/en/knowledge-network/' },
      { text: 'Core features', link: '/en/features/' },
    ],
  },
  {
    text: 'Operations and reference',
    items: [
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
  plugins: [isolateSsrRuntime],
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
        lang: 'en-US',
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
