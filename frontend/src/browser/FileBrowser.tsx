import { useCallback, useEffect, useRef, useState, type ComponentType, type KeyboardEvent, type ReactNode } from 'react'
import { ContextMenu, type MenuItem, type MenuState } from '../components/ContextMenu'
import { IconButton } from '../components/IconButton'
import {
  ChevronIcon,
  CloseIcon,
  DesktopIcon,
  DocumentsIcon,
  DownloadIcon,
  DriveIcon,
  EyeIcon,
  EyeOffIcon,
  HomeIcon,
  PinIcon,
  PlusIcon,
  RefreshIcon,
  SearchIcon,
} from '../components/icons'
import {
  call,
  setPreference,
  toError,
  type AppSettings,
  type FsEntry,
  type PinnedFolder,
  type QuickLocation,
} from '../lib/bridge'
import { cls } from '../lib/cls'
import { samePath } from '../lib/format'
import { explorerExtension, REVEAL_EVENT, type ExplorerContext } from '../lib/platform'
import { convertToolFor, extOf, isImage, isPdf, type CategoryId, type ToolId } from '../lib/workspace'
import { PathBar } from './PathBar'
import { PinnedList } from './PinnedList'
import { TreeView } from './TreeView'
import { useDirectoryTree } from './useDirectoryTree'

const LOCATION_ICONS: Record<QuickLocation['kind'], ComponentType<{ size?: number; className?: string }>> = {
  home: HomeIcon,
  desktop: DesktopIcon,
  documents: DocumentsIcon,
  downloads: DownloadIcon,
  drive: DriveIcon,
}

const NO_PINS: PinnedFolder[] = []

interface Props {
  selected: FsEntry | null
  onSelect: (entry: FsEntry | null) => void
  onOpenInTool: (target: ToolId | CategoryId, path: string) => void
  /** Bumped when a tool writes files; the visible folders are re-read. */
  filesVersion: number
}

interface Toast {
  text: string
  error: boolean
}

export function FileBrowser({ selected, onSelect, onOpenInTool, filesVersion }: Props) {
  const [settings, setSettings] = useState<AppSettings | null>(null)
  const [locations, setLocations] = useState<QuickLocation[]>([])
  const [nav, setNav] = useState<{ stack: string[]; index: number }>({ stack: [], index: -1 })
  const [filter, setFilter] = useState('')
  const [menu, setMenu] = useState<MenuState | null>(null)
  const [toast, setToast] = useState<Toast | null>(null)
  const [sections, setSections] = useState({ pinned: true, locations: true })
  const [dropping, setDropping] = useState(false)
  const ext = explorerExtension()
  const shell = !ext?.hideShellItems

  const root = nav.index >= 0 ? nav.stack[nav.index] : null
  const showHidden = settings?.show_hidden ?? false
  const pins = settings?.pinned ?? NO_PINS
  const tree = useDirectoryTree(root, showHidden, filter)
  const listing = tree.rootState?.status === 'ready' ? tree.rootState.listing : undefined

  const notify = useCallback((err: unknown) => setToast({ text: toError(err).message, error: true }), [])
  const closeMenu = useCallback(() => setMenu(null), [])

  const refreshTree = useRef(tree.refresh)
  useEffect(() => {
    refreshTree.current = tree.refresh
  })
  useEffect(() => {
    if (filesVersion) refreshTree.current()
  }, [filesVersion])

  useEffect(() => {
    if (!toast) return
    const t = window.setTimeout(() => setToast(null), 3500)
    return () => window.clearTimeout(t)
  }, [toast])

  // --- navigation ------------------------------------------------------------

  const visit = useCallback((path: string) => {
    setNav((h) =>
      samePath(h.stack[h.index], path) ? h : { stack: [...h.stack.slice(0, h.index + 1), path], index: h.index + 1 },
    )
    setFilter('')
  }, [])

  const goBack = () => setNav((h) => ({ ...h, index: Math.max(0, h.index - 1) }))
  const goForward = () => setNav((h) => ({ ...h, index: Math.min(h.stack.length - 1, h.index + 1) }))
  const goUp = () => {
    if (listing?.parent) visit(listing.parent)
  }

  // "Show in folder" from elsewhere in the UI, for hosts without an OS file manager (REVEAL_EVENT).
  useEffect(() => {
    const onReveal = (e: Event) => {
      const path = (e as CustomEvent<string>).detail
      if (typeof path === 'string') visit(path.replace(/[\\/][^\\/]*$/, '') || path)
    }
    window.addEventListener(REVEAL_EVENT, onReveal)
    return () => window.removeEventListener(REVEAL_EVENT, onReveal)
  }, [visit])

  async function submitPath(text: string) {
    visit(await call('resolve_dir', text))
  }

  useEffect(() => {
    if (root) setPreference('browser_root', root).catch(() => {})
  }, [root])

  // Initial load: settings, locations, and the last folder (falling back to Home).
  useEffect(() => {
    let active = true
    ;(async () => {
      try {
        const [s, locs] = await Promise.all([call('get_settings'), call('get_locations')])
        if (!active) return
        setSettings(s)
        setLocations(locs)
        for (const candidate of [s.browser_root, locs[0]?.path]) {
          if (!candidate) continue
          try {
            const path = await call('resolve_dir', candidate)
            if (active) visit(path)
            return
          } catch {
            // Last folder is gone; try the next candidate.
          }
        }
      } catch (err) {
        if (active) notify(err)
      }
    })()
    return () => {
      active = false
    }
  }, [visit, notify])

  // --- pins & preferences ----------------------------------------------------

  const isPinned = useCallback((path: string) => pins.some((p) => samePath(p.path, path)), [pins])

  const pinAt = (path: string, index: number | null = null) =>
    call('pin_folder', path, index).then((pinned) => setSettings((s) => s && { ...s, pinned }), notify)

  const unpin = (path: string) =>
    call('unpin_folder', path).then((pinned) => setSettings((s) => s && { ...s, pinned }), notify)

  const togglePin = (path: string) => (isPinned(path) ? unpin(path) : pinAt(path))

  async function pinFromDialog() {
    try {
      const path = await call('pick_folder', root ?? '')
      if (path) await pinAt(path)
    } catch (err) {
      notify(err)
    }
  }

  function toggleHidden() {
    const next = !showHidden
    setSettings((s) => s && { ...s, show_hidden: next })
    setPreference('show_hidden', next).catch(notify)
  }

  // --- actions ---------------------------------------------------------------

  const openPath = (path: string) => call('open_path', path).catch(notify)
  const revealPath = (path: string) => call('reveal_path', path).catch(notify)
  const copyPath = (path: string) =>
    navigator.clipboard.writeText(path).then(() => setToast({ text: 'Path copied', error: false }), notify)

  const activate = (entry: FsEntry) => (entry.is_dir ? visit(entry.path) : openPath(entry.path))

  const ctx: ExplorerContext = {
    root,
    refresh: tree.refresh,
    visit,
    notify,
    toast: (text: string) => setToast({ text, error: false }),
  }

  function dirMenu(path: string): MenuItem[] {
    return [
      { label: 'Open', onSelect: () => visit(path) },
      { label: isPinned(path) ? 'Unpin' : 'Pin', onSelect: () => togglePin(path) },
      'separator',
      ...(shell ? [{ label: 'Open in File Explorer', onSelect: () => openPath(path) }] : []),
      { label: 'Copy path', onSelect: () => copyPath(path) },
    ]
  }

  function entryMenu(entry: FsEntry): MenuItem[] {
    const extra = ext?.entryItems?.(entry, ctx) ?? []
    if (entry.is_dir) return extra.length ? [...dirMenu(entry.path), 'separator', ...extra] : dirMenu(entry.path)
    const convertTool = convertToolFor(entry.path)
    const pdfItems: MenuItem[] = isPdf(entry.path)
      ? [
          { label: 'Open in PDF tools', onSelect: () => onOpenInTool('pdf-pages', entry.path) },
          { label: 'Add to Merge PDF', onSelect: () => onOpenInTool('pdf-merge', entry.path) },
          { label: 'Edit PDF', onSelect: () => onOpenInTool('edit-pdf', entry.path) },
          { label: 'Convert from PDF', onSelect: () => onOpenInTool('from-pdf', entry.path) },
          { label: 'Sign PDF', onSelect: () => onOpenInTool('sign-pdf', entry.path) },
          { label: 'Protect PDF', onSelect: () => onOpenInTool('protect-pdf', entry.path) },
          { label: 'Print…', onSelect: () => onOpenInTool('print-pdf', entry.path) },
          'separator',
        ]
      : isImage(entry.path)
        ? [
            { label: 'Edit photo', onSelect: () => onOpenInTool('photo-editor', entry.path) },
            { label: 'Compress image', onSelect: () => onOpenInTool('img-compress', entry.path) },
            { label: 'Resize image', onSelect: () => onOpenInTool('img-resize', entry.path) },
            { label: 'Crop image', onSelect: () => onOpenInTool('img-crop', entry.path) },
            { label: 'Add to collage', onSelect: () => onOpenInTool('img-collage', entry.path) },
            { label: 'Remove background', onSelect: () => onOpenInTool('img-remove-bg', entry.path) },
            { label: 'Upscale image', onSelect: () => onOpenInTool('img-upscale', entry.path) },
            ...(convertTool ? [{ label: 'Convert to PDF', onSelect: () => onOpenInTool(convertTool, entry.path) }] : []),
            'separator' as const,
          ]
        : convertTool
        ? [{ label: 'Convert to PDF', onSelect: () => onOpenInTool(convertTool, entry.path) }, 'separator']
        : extOf(entry.path) === 'tex'
          ? [{ label: 'Open in LaTeX editor', onSelect: () => onOpenInTool('latex', entry.path) }, 'separator']
          : []
    return [
      { label: 'Open', onSelect: () => openPath(entry.path) },
      ...(shell ? [{ label: 'Show in File Explorer', onSelect: () => revealPath(entry.path) }] : []),
      'separator',
      ...pdfItems,
      ...(extra.length ? [...extra, 'separator' as const] : []),
      { label: 'Copy path', onSelect: () => copyPath(entry.path) },
    ]
  }

  function pinMenu(pin: PinnedFolder, index: number): MenuItem[] {
    return [
      { label: 'Open', onSelect: () => visit(pin.path), disabled: !pin.exists },
      { label: 'Unpin', onSelect: () => unpin(pin.path) },
      'separator',
      { label: 'Move up', onSelect: () => pinAt(pin.path, index - 1), disabled: index === 0 },
      { label: 'Move down', onSelect: () => pinAt(pin.path, index + 1), disabled: index === pins.length - 1 },
      'separator',
      ...(shell ? [{ label: 'Open in File Explorer', onSelect: () => openPath(pin.path), disabled: !pin.exists }] : []),
      { label: 'Copy path', onSelect: () => copyPath(pin.path) },
    ]
  }

  function folderMenu(path: string): MenuItem[] {
    return [
      { label: isPinned(path) ? 'Unpin this folder' : 'Pin this folder', onSelect: () => togglePin(path) },
      { label: 'Refresh', onSelect: tree.refresh },
      { label: showHidden ? 'Hide hidden items' : 'Show hidden items', onSelect: toggleHidden },
      'separator',
      ...(ext?.folderItems ? [...ext.folderItems(path, ctx), 'separator' as const] : []),
      ...(shell ? [{ label: 'Open in File Explorer', onSelect: () => openPath(path) }] : []),
      { label: 'Copy path', onSelect: () => copyPath(path) },
    ]
  }

  function onPanelKeyDown(e: KeyboardEvent) {
    if (e.altKey && e.key === 'ArrowLeft') goBack()
    else if (e.altKey && e.key === 'ArrowRight') goForward()
    else return
    e.preventDefault()
  }

  // --- render ----------------------------------------------------------------

  let empty: ReactNode = 'Loading…'
  if (tree.rootState?.status === 'error') empty = <span className="is-error">{tree.rootState.error}</span>
  else if (listing && filter.trim()) empty = `No matches for “${filter.trim()}” in open folders`
  else if (listing) empty = 'This folder is empty'

  const rootPinned = root !== null && isPinned(root)

  return (
    <div
      className={cls('browser', dropping && 'is-dropping')}
      data-browser-state={tree.rootState?.status ?? 'loading'}
      onKeyDown={onPanelKeyDown}
      onDragOver={(e) => {
        if (!ext?.dropFiles || !root || !e.dataTransfer.types.includes('Files')) return
        e.preventDefault()
        setDropping(true)
      }}
      onDragLeave={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setDropping(false)
      }}
      onDrop={(e) => {
        setDropping(false)
        if (!ext?.dropFiles || !root || !e.dataTransfer.files.length) return
        e.preventDefault()
        ext.dropFiles([...e.dataTransfer.files], root, ctx)
      }}
    >
      <div className="browser-head">
        <span className="browser-title">{ext?.title ?? 'Explorer'}</span>
        <div className="browser-actions">
          {ext?.headerActions?.(ctx)}
          <IconButton
            label={showHidden ? 'Hide hidden items' : 'Show hidden items'}
            active={showHidden}
            onClick={toggleHidden}
          >
            {showHidden ? <EyeIcon size={15} /> : <EyeOffIcon size={15} />}
          </IconButton>
          <IconButton label="Refresh" onClick={tree.refresh}>
            <RefreshIcon size={15} />
          </IconButton>
        </div>
      </div>

      <Section
        title="Pinned"
        open={sections.pinned}
        onToggle={() => setSections((s) => ({ ...s, pinned: !s.pinned }))}
        action={
          <IconButton label="Pin a folder…" onClick={pinFromDialog}>
            <PlusIcon size={14} />
          </IconButton>
        }
      >
        <PinnedList
          pins={pins}
          activeRoot={root}
          onOpen={(pin) => visit(pin.path)}
          onPinAt={(path, index) => pinAt(path, index)}
          onMenu={(e, pin, index) => setMenu({ x: e.clientX, y: e.clientY, items: pinMenu(pin, index) })}
        />
      </Section>

      <Section
        title="Locations"
        open={sections.locations}
        onToggle={() => setSections((s) => ({ ...s, locations: !s.locations }))}
      >
        <ul className="nav-list">
          {locations.map((loc) => {
            const Icon = LOCATION_ICONS[loc.kind]
            return (
              <li key={loc.path}>
                <button
                  type="button"
                  className={cls('nav-row', samePath(loc.path, root) && 'is-active')}
                  title={loc.path}
                  onClick={() => visit(loc.path)}
                  onContextMenu={(e) => {
                    e.preventDefault()
                    setMenu({ x: e.clientX, y: e.clientY, items: dirMenu(loc.path) })
                  }}
                >
                  <Icon size={15} className="nav-icon" />
                  <span className="nav-label">{loc.label}</span>
                </button>
              </li>
            )
          })}
        </ul>
      </Section>

      <div className="tree-section">
        <PathBar
          root={root}
          listing={listing}
          canBack={nav.index > 0}
          canForward={nav.index < nav.stack.length - 1}
          onBack={goBack}
          onForward={goForward}
          onUp={goUp}
          onSubmitPath={submitPath}
          onCrumb={visit}
          trailing={
            <IconButton
              label={rootPinned ? 'Unpin this folder' : 'Pin this folder'}
              active={rootPinned}
              disabled={!root}
              onClick={() => root && togglePin(root)}
            >
              <PinIcon size={15} />
            </IconButton>
          }
        />

        <div className="filter">
          <SearchIcon size={14} className="filter-icon" />
          <input
            value={filter}
            placeholder={listing ? `Filter ${listing.name}` : 'Filter'}
            spellCheck={false}
            aria-label="Filter files"
            onChange={(e) => setFilter(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Escape') setFilter('')
              if (e.key === 'ArrowDown') {
                e.preventDefault()
                document.querySelector<HTMLElement>('.tree')?.focus()
              }
            }}
          />
          {filter && (
            <button type="button" className="filter-clear" aria-label="Clear filter" onClick={() => setFilter('')}>
              <CloseIcon size={12} />
            </button>
          )}
        </div>

        <TreeView
          rows={tree.rows}
          selectedPath={selected?.path ?? null}
          isPinned={isPinned}
          empty={empty}
          onSelect={onSelect}
          onSetOpen={tree.setOpen}
          onActivate={activate}
          onUp={goUp}
          onEntryMenu={(e, entry) => setMenu({ x: e.clientX, y: e.clientY, items: entryMenu(entry) })}
          onBackgroundMenu={(e) => root && setMenu({ x: e.clientX, y: e.clientY, items: folderMenu(root) })}
        />
      </div>

      {toast && (
        <div className={cls('toast', toast.error && 'is-error')} role="status">
          {toast.text}
        </div>
      )}
      {menu && <ContextMenu menu={menu} onClose={closeMenu} />}
    </div>
  )
}

function Section({
  title,
  open,
  onToggle,
  action,
  children,
}: {
  title: string
  open: boolean
  onToggle: () => void
  action?: ReactNode
  children: ReactNode
}) {
  return (
    <section className="section">
      <div className="section-head">
        <button type="button" className="section-toggle" aria-expanded={open} onClick={onToggle}>
          <ChevronIcon size={12} className={cls('chev', open && 'is-open')} />
          {title}
        </button>
        {action}
      </div>
      {open && children}
    </section>
  )
}
