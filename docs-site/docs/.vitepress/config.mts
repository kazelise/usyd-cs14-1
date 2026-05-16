import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'CS14 Research Platform',
  description: 'Researcher and acceptance documentation for the COMP5703 CS14 social-media survey platform.',
  cleanUrls: true,
  lastUpdated: true,
  markdown: {
    theme: {
      light: 'github-light',
      dark: 'github-dark'
    }
  },
  themeConfig: {
    logo: { src: '/logo.svg', alt: 'CS14' },
    nav: [
      { text: 'Guide', link: '/guide/researcher-workflow' },
      { text: 'Data', link: '/guide/data-export' },
      { text: 'Project', link: '/project/architecture' }
    ],
    sidebar: [
      {
        text: 'Researcher Operations',
        items: [
          { text: 'Overview', link: '/' },
          { text: 'Researcher Workflow', link: '/guide/researcher-workflow' },
          { text: 'Data Export & Translations', link: '/guide/data-export' },
          { text: 'Platform Style Gallery', link: '/guide/platform-styles' },
          { text: 'Social Post Fetching', link: '/guide/social-post-fetching' },
          { text: 'Calibration & Privacy', link: '/guide/calibration-privacy' },
          { text: 'Attention Confidence', link: '/guide/attention-confidence' }
        ]
      },
      {
        text: 'Project Design',
        items: [
          { text: 'System Architecture', link: '/project/architecture' },
          { text: 'Database Design', link: '/project/database' },
          { text: 'API Reference', link: '/project/api-reference' },
          { text: 'Frontend Design', link: '/project/frontend-design' },
          { text: 'Local Setup & Deployment Prep', link: '/project/setup-deployment' },
          { text: 'PDF/MVP Coverage Matrix', link: '/project/acceptance-matrix' }
        ]
      }
    ],
    search: {
      provider: 'local'
    },
    outline: {
      level: [2, 3]
    },
    socialLinks: []
  },
  head: [
    ['meta', { name: 'theme-color', content: '#00a7a0' }]
  ]
})
