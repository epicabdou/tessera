import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { FileBrowser } from './browser/FileBrowser'
import { CommandPalette } from './components/CommandPalette'
import { IconButton } from './components/IconButton'
import { PanelRightIcon, SearchIcon } from './components/icons'
import { Resizer } from './components/Resizer'
import { StatusBar } from './components/StatusBar'
import { StatusPill } from './components/StatusPill'
import { call, getApi, setPreference, type BridgeState, type FsEntry } from './lib/bridge'
import { cls } from './lib/cls'
import { WorkspaceContext, type CategoryId, type ToolId, type ToolRequest, type Workspace } from './lib/workspace'
import './pdf/pdf.css'
import { PdfDocProvider, ThumbProvider } from './pdf/PdfProviders'
import { PreviewPanel } from './preview/PreviewPanel'
import { ImageDocProvider } from './images/components'
import { CATEGORIES, categoryOf, SECTIONS, type SectionId } from './tools/registry'

const EXPLORER = { min: 220, max: 560, default: 280 }
const PREVIEW = { min: 240, max: 820, default: 340 }
/** Space the tools always keep between the two side panels (plus the window padding and gaps). */
const MAIN_MIN = 460

const clamp = (w: number, lo: number, hi: number) => Math.round(Math.min(hi, Math.max(lo, w)))

interface Nav {
  category: CategoryId
  /** Last tool used in each category. */
  tools: Record<CategoryId, ToolId>
  /** Last category used in each section. */
  sections: Record<SectionId, CategoryId>
}

const INITIAL_NAV: Nav = {
  category: CATEGORIES[0].id,
  tools: Object.fromEntries(CATEGORIES.map((c) => [c.id, c.tools[0].id])) as Record<CategoryId, ToolId>,
  sections: Object.fromEntries(SECTIONS.map((s) => [s.id, CATEGORIES.find((c) => c.section === s.id)!.id])) as Record<SectionId, CategoryId>,
}

/** Go to a category, remembering it as its section's current one. */
const goCategory = (n: Nav, category: CategoryId): Nav => ({ ...n, category, sections: { ...n.sections, [CATEGORIES.find((c) => c.id === category)!.section]: category } })

export default function App() {
  const [nav, setNav] = useState<Nav>(INITIAL_NAV)
  const [bridge, setBridge] = useState<BridgeState>('connecting')
  const [selected, setSelected] = useState<FsEntry | null>(null)
  const [request, setRequest] = useState<ToolRequest | null>(null)
  const [filesVersion, setFilesVersion] = useState(0)
  const [explorerWidth, setExplorerWidth] = useState(EXPLORER.default)
  const [previewWidth, setPreviewWidth] = useState(PREVIEW.default)
  const [previewOpen, setPreviewOpen] = useState(true)
  const [paletteOpen, setPaletteOpen] = useState(false)
  const navRef = useRef(nav)

  useEffect(() => {
    navRef.current = nav
  }, [nav])

  useEffect(() => {
    getApi().then(
      () => setBridge('connected'),
      () => setBridge('unavailable'),
    )
    call('get_settings').then(
      (s) => {
        setExplorerWidth(clamp(s.sidebar_width, EXPLORER.min, EXPLORER.max))
        setPreviewWidth(clamp(s.preview_width, PREVIEW.min, PREVIEW.max))
        setPreviewOpen(s.preview_open)
      },
      () => {},
    )
  }, [])

  // Exposed for the --self-test probe.
  useEffect(() => {
    document.documentElement.dataset.bridge = bridge
  }, [bridge])

  // Ctrl+K: find a tool.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && !e.shiftKey && !e.altKey && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setPaletteOpen((o) => !o)
      }
    }
    window.addEventListener('keydown', onKey, true)
    return () => window.removeEventListener('keydown', onKey, true)
  }, [])

  const showTool = useCallback((tool: ToolId) => {
    const category = categoryOf(tool).id
    setNav((n) => ({ ...goCategory(n, category), tools: { ...n.tools, [category]: tool } }))
  }, [])

  const openInTool = useCallback(
    (target: ToolId | CategoryId, path: string) => {
      let tool = target as ToolId
      const category = CATEGORIES.find((c) => c.id === target)
      if (category) {
        // A single file opens in the last page tool; Merge is for several files.
        tool = navRef.current.tools[category.id]
        if (tool === 'pdf-merge') tool = 'pdf-organize'
      }
      showTool(tool)
      setRequest((r) => ({ tool, path, nonce: (r?.nonce ?? 0) + 1 }))
    },
    [showTool],
  )

  const filesChanged = useCallback(() => setFilesVersion((v) => v + 1), [])

  const workspace = useMemo<Workspace>(
    () => ({ selected, request, openInTool, filesChanged }),
    [selected, request, openInTool, filesChanged],
  )

  const togglePreview = (open: boolean) => {
    setPreviewOpen(open)
    setPreference('preview_open', open).catch(() => {})
  }

  // Neither side panel may squeeze the tools below MAIN_MIN.
  const room = window.innerWidth - MAIN_MIN
  const explorerMax = Math.max(EXPLORER.min, Math.min(EXPLORER.max, room - (previewOpen ? previewWidth : 0)))
  const previewMax = Math.max(PREVIEW.min, Math.min(PREVIEW.max, room - explorerWidth))

  const activeCategory = CATEGORIES.find((c) => c.id === nav.category) ?? CATEGORIES[0]
  const activeSection = activeCategory.section
  const activeTool = nav.tools[activeCategory.id]

  return (
    <WorkspaceContext.Provider value={workspace}>
      <ThumbProvider>
        <PdfDocProvider>
          <ImageDocProvider>
          <div className="app-bg" aria-hidden="true" />
          <div className="shell">
            <aside className="panel sidebar" style={{ width: explorerWidth }}>
              <FileBrowser selected={selected} onSelect={setSelected} onOpenInTool={openInTool} filesVersion={filesVersion} />
            </aside>

            <Resizer
              label="Resize explorer"
              panel="left"
              width={explorerWidth}
              min={EXPLORER.min}
              max={explorerMax}
              defaultWidth={EXPLORER.default}
              onResize={setExplorerWidth}
              onCommit={(w) => setPreference('sidebar_width', w).catch(() => {})}
            />

            <div className="panel main">
              <header className="topbar">
                <div className="brand" title="Toolbox">
                  <img src="./favicon.svg" alt="" width={26} height={26} />
                  <span>Toolbox</span>
                </div>
                <nav className="sections" role="tablist" aria-label="Sections">
                  {SECTIONS.map((s) => (
                    <button
                      key={s.id}
                      type="button"
                      role="tab"
                      aria-selected={s.id === activeSection}
                      className={cls('section-tab', s.id === activeSection && 'is-active')}
                      title={s.label}
                      onClick={() => setNav((n) => goCategory(n, n.sections[s.id]))}
                    >
                      {s.icon}
                      <span className="section-label">{s.label}</span>
                    </button>
                  ))}
                </nav>
                <nav className="tabs" role="tablist" aria-label="Categories">
                  {CATEGORIES.filter((c) => c.section === activeSection).map((c) => (
                    <button
                      key={c.id}
                      type="button"
                      role="tab"
                      aria-selected={c.id === activeCategory.id}
                      className={cls('tab', c.id === activeCategory.id && 'is-active')}
                      title={c.label}
                      onClick={() => setNav((n) => goCategory(n, c.id))}
                    >
                      {c.icon}
                      <span className="tab-label">{c.short}</span>
                    </button>
                  ))}
                </nav>
                <div className="topbar-end">
                  <button type="button" className="search-trigger" onClick={() => setPaletteOpen(true)} title="Find a tool (Ctrl+K)">
                    <SearchIcon size={15} />
                    <span className="search-label">Find a tool</span>
                    <kbd>Ctrl K</kbd>
                  </button>
                  <StatusPill bridge={bridge} />
                  <IconButton label={previewOpen ? 'Hide preview' : 'Show preview'} active={previewOpen} onClick={() => togglePreview(!previewOpen)}>
                    <PanelRightIcon size={16} />
                  </IconButton>
                </div>
              </header>

              {/* A category with a single tool needs no tool row. */}
              <nav className="toolstrip" role="tablist" aria-label={`${activeCategory.label} tools`} hidden={activeCategory.tools.length < 2}>
                <span className="toolstrip-title">{activeCategory.label}</span>
                {activeCategory.tools.map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    role="tab"
                    aria-selected={t.id === activeTool}
                    className={cls('tool-pill', t.id === activeTool && 'is-active')}
                    title={t.hint}
                    onClick={() => showTool(t.id)}
                  >
                    {t.icon}
                    <span>{t.label}</span>
                  </button>
                ))}
              </nav>

              <main className="content">
                {/* Every tool stays mounted so switching keeps its state. */}
                {CATEGORIES.flatMap((c) => c.tools).map(({ id, component: Tool }) => (
                  <div key={id} role="tabpanel" hidden={id !== activeTool || categoryOf(id).id !== activeCategory.id}>
                    <Tool />
                  </div>
                ))}
              </main>

              <StatusBar entry={selected} />
            </div>

            {previewOpen && (
              <>
                <Resizer
                  label="Resize preview"
                  panel="right"
                  width={previewWidth}
                  min={PREVIEW.min}
                  max={previewMax}
                  defaultWidth={PREVIEW.default}
                  onResize={setPreviewWidth}
                  onCommit={(w) => setPreference('preview_width', w).catch(() => {})}
                />
                <aside className="panel preview-aside" style={{ width: previewWidth }}>
                  <PreviewPanel filesVersion={filesVersion} onClose={() => togglePreview(false)} />
                </aside>
              </>
            )}
          </div>
          {paletteOpen && (
            <CommandPalette
              current={activeTool}
              onClose={() => setPaletteOpen(false)}
              onPick={(id) => {
                showTool(id)
                setPaletteOpen(false)
              }}
            />
          )}
          </ImageDocProvider>
        </PdfDocProvider>
      </ThumbProvider>
    </WorkspaceContext.Provider>
  )
}
