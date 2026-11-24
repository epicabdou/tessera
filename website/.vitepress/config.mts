import { defineConfig } from 'vitepress'

export const REPO = 'https://github.com/epicabdou/tilepress'
const BASE = '/tilepress/'
const SITE = `https://epicabdou.github.io${BASE}`
const DESCRIPTION =
  'Free and open-source PDF and image tools for Windows. Merge, convert, compress, sign, OCR, edit photos and more, on your own computer: nothing is uploaded.'

export default defineConfig({
  lang: 'en-US',
  title: 'Tilepress',
  titleTemplate: ':title · Tilepress',
  description: DESCRIPTION,
  base: BASE,
  cleanUrls: true,
  lastUpdated: true,
  sitemap: { hostname: SITE },

  head: [
    ['link', { rel: 'icon', type: 'image/svg+xml', href: `${BASE}favicon.svg` }],
    ['meta', { name: 'theme-color', content: '#7c6cff' }],
    ['meta', { property: 'og:type', content: 'website' }],
    ['meta', { property: 'og:site_name', content: 'Tilepress' }],
    ['meta', { property: 'og:title', content: 'Tilepress: free, local PDF and image tools' }],
    ['meta', { property: 'og:description', content: DESCRIPTION }],
    ['meta', { property: 'og:image', content: `${SITE}og.png` }],
    ['meta', { name: 'twitter:card', content: 'summary_large_image' }],
  ],

  themeConfig: {
    logo: { src: '/favicon.svg', alt: '' },
    siteTitle: 'Tilepress',

    nav: [
      { text: 'Docs', link: '/docs/', activeMatch: '^/docs/' },
      { text: 'Download', link: '/download' },
      { text: 'Support', link: '/support' },
    ],

    sidebar: {
      '/docs/': [
        {
          text: 'Start here',
          items: [
            { text: 'Getting started', link: '/docs/' },
            { text: 'The Tilepress window', link: '/docs/interface' },
            { text: 'History', link: '/docs/history' },
            { text: 'Privacy: what stays on your PC', link: '/docs/privacy' },
          ],
        },
        {
          text: 'Documents',
          items: [
            { text: 'Combine, split & pages', link: '/docs/pdf-pages' },
            { text: 'Convert to PDF', link: '/docs/to-pdf' },
            { text: 'Convert from PDF', link: '/docs/from-pdf' },
            { text: 'Edit, forms & OCR', link: '/docs/edit' },
            { text: 'Security, signing & size', link: '/docs/security' },
            { text: 'Printing', link: '/docs/print' },
            { text: 'LaTeX', link: '/docs/latex' },
          ],
        },
        {
          text: 'Images',
          items: [
            { text: 'Format & size', link: '/docs/img-optimize' },
            { text: 'Crop, rotate, collage & capture', link: '/docs/img-layout' },
            { text: 'AI enhancements', link: '/docs/img-ai' },
            { text: 'Edit & brand', link: '/docs/img-edit' },
          ],
        },
        {
          text: 'Developers',
          items: [{ text: 'Build from source', link: '/docs/build' }],
        },
      ],
    },

    outline: { level: [2, 3], label: 'On this page' },
    search: { provider: 'local' },
    socialLinks: [{ icon: 'github', link: REPO }],
    editLink: { pattern: `${REPO}/edit/main/website/:path`, text: 'Improve this page on GitHub' },
    lastUpdated: { text: 'Updated' },
    footer: {
      message:
        'Free software under the <a href="https://www.gnu.org/licenses/gpl-3.0.html">GNU GPL v3</a>. iLovePDF and iLoveIMG are trademarks of their owners; Tilepress is not affiliated with them.',
      copyright: 'Copyright © 2026 epicabdou',
    },
  },
})
