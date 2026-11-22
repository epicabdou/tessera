import type { Theme } from 'vitepress'
import DefaultTheme from 'vitepress/theme'
import Comparison from './components/Comparison.vue'
import DownloadPanel from './components/DownloadPanel.vue'
import Showcase from './components/Showcase.vue'
import ToolGrid from './components/ToolGrid.vue'
import './style.css'

export default {
  extends: DefaultTheme,
  enhanceApp({ app }) {
    app.component('Comparison', Comparison)
    app.component('DownloadPanel', DownloadPanel)
    app.component('Showcase', Showcase)
    app.component('ToolGrid', ToolGrid)
  },
} satisfies Theme
