import type { ReactNode } from 'react'
import type { MenuItem } from '../components/ContextMenu'
import type { FsEntry } from './bridge'

/**
 * Extension points for an app that embeds this UI with a different host (Tilepress Web runs it in
 * the browser, against a server). The desktop app sets none of them. An embedding app fills them
 * in before App first renders, so it never needs to edit these components.
 *
 * See also `setTransport` in ./bridge (where calls go), the `topbarEnd` and `toolBadge` props of
 * App, and `CustomToolIds` / `CustomCategoryIds` in ./workspace (extra tools).
 */

/** What an Explorer extension can do to the Explorer it's shown in. */
export interface ExplorerContext {
  /** The folder on screen. */
  root: string | null
  refresh: () => void
  visit: (path: string) => void
  notify: (err: unknown) => void
  toast: (text: string) => void
}

export interface ExplorerExtension {
  /** The Explorer's title (default "Explorer"). */
  title?: string
  /** Buttons in the Explorer header (before Show hidden / Refresh). */
  headerActions?: (ctx: ExplorerContext) => ReactNode
  /** Extra items for a file's or folder's context menu. */
  entryItems?: (entry: FsEntry, ctx: ExplorerContext) => MenuItem[]
  /** Extra items for the open folder's background menu. */
  folderItems?: (path: string, ctx: ExplorerContext) => MenuItem[]
  /** Files dropped from the computer onto the Explorer. */
  dropFiles?: (files: File[], folder: string, ctx: ExplorerContext) => void
  /** Leave out the items that need the OS shell (Open in File Explorer…). */
  hideShellItems?: boolean
}

let explorer: ExplorerExtension | null = null

export function extendExplorer(ext: ExplorerExtension) {
  explorer = ext
}

export function explorerExtension(): ExplorerExtension | null {
  return explorer
}

/** Window event (detail: a path): show this file or folder in the Explorer. */
export const REVEAL_EVENT = 'tilepress:reveal'
