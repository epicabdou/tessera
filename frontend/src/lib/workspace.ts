import { createContext, useContext, useEffect, useRef } from 'react'
import type { FsEntry } from './bridge'

/**
 * Tools and categories an app embedding this UI adds (see lib/platform.ts). It declares their ids
 * by augmenting these interfaces, e.g. `declare module '…/lib/workspace' { interface CustomToolIds
 * { workflows: true } }`, then adds the tool to CATEGORIES. Both are empty in the desktop app.
 */
export interface CustomCategoryIds {}
export interface CustomToolIds {}

export type CategoryId =
  | 'img-optimize'
  | 'img-layout'
  | 'img-ai'
  | 'img-edit'
  | 'pdf-pages'
  | 'to-pdf'
  | 'from-pdf'
  | 'edit'
  | 'security'
  | 'print'
  | 'latex'
  | keyof CustomCategoryIds

export type ToolId =
  | 'pdf-merge'
  | 'pdf-split'
  | 'pdf-organize'
  | 'pdf-rotate'
  | 'pdf-crop'
  | 'pdf-numbers'
  | 'to-pdf-word'
  | 'to-pdf-powerpoint'
  | 'to-pdf-excel'
  | 'to-pdf-images'
  | 'to-pdf-html'
  | 'to-pdf-markdown'
  | 'from-pdf-word'
  | 'from-pdf-powerpoint'
  | 'from-pdf-excel'
  | 'from-pdf-images'
  | 'from-pdf-markdown'
  | 'edit-pdf'
  | 'ocr-pdf'
  | 'pdf-forms'
  | 'watermark'
  | 'protect-pdf'
  | 'sign-pdf'
  | 'compress-pdf'
  | 'repair-pdf'
  | 'print-pdf'
  | 'latex'
  | 'img-compress'
  | 'img-resize'
  | 'img-to-jpg'
  | 'img-from-jpg'
  | 'img-crop'
  | 'img-rotate'
  | 'img-collage'
  | 'html-to-image'
  | 'img-upscale'
  | 'img-remove-bg'
  | 'img-blur-faces'
  | 'photo-editor'
  | 'img-watermark'
  | keyof CustomToolIds

/** "Open this path in that tool", e.g. from the file browser's context menu. */
export interface ToolRequest {
  tool: ToolId
  path: string
  nonce: number
}

export interface Workspace {
  /** Item selected in the file browser. */
  selected: FsEntry | null
  request: ToolRequest | null
  /** Open `path` in a tool, or in the last-used tool of a category. */
  openInTool: (target: ToolId | CategoryId, path: string) => void
  /** Tell the Explorer that files were written, so it re-reads what's on screen. */
  filesChanged: () => void
}

export const WorkspaceContext = createContext<Workspace | null>(null)

export function useWorkspace(): Workspace {
  const ws = useContext(WorkspaceContext)
  if (!ws) throw new Error('useWorkspace must be used inside WorkspaceContext')
  return ws
}

/** Runs `handle` once for each new request aimed at `tool`. */
export function useToolRequest(tool: ToolId, handle: (path: string) => void) {
  const { request } = useWorkspace()
  const handled = useRef(0)
  const latest = useRef(handle)

  useEffect(() => {
    latest.current = handle
  })

  useEffect(() => {
    if (request && request.tool === tool && request.nonce !== handled.current) {
      handled.current = request.nonce
      latest.current(request.path)
    }
  }, [request, tool])
}

export const isPdf = (path: string | null | undefined) => !!path && path.toLowerCase().endsWith('.pdf')

export const extOf = (path: string) => (path.match(/\.([^.\\/]+)$/)?.[1] ?? '').toLowerCase()

/** Images the image tools read (kept in step with services/images/imageio.py). */
export const IMAGE_EXTS = ['jpg', 'jpeg', 'jfif', 'png', 'gif', 'bmp', 'tif', 'tiff', 'webp', 'avif', 'ico', 'heic', 'heif']
export const JPEG_EXTS = ['jpg', 'jpeg', 'jfif']
export const isImage = (path: string | null | undefined) => !!path && IMAGE_EXTS.includes(extOf(path))

/** File extensions each Convert-to-PDF tool accepts (kept in step with the Python side). */
export const CONVERT_EXTS: Partial<Record<ToolId, string[]>> = {
  'to-pdf-word': ['doc', 'docx', 'docm', 'dot', 'dotx', 'dotm', 'rtf', 'odt'],
  'to-pdf-powerpoint': ['ppt', 'pptx', 'pptm', 'pps', 'ppsx', 'pot', 'potx', 'odp'],
  'to-pdf-excel': ['xls', 'xlsx', 'xlsm', 'xlsb', 'xltx', 'xltm', 'ods', 'csv'],
  'to-pdf-images': ['jpg', 'jpeg', 'jfif', 'png', 'gif', 'bmp', 'tif', 'tiff', 'webp'],
  'to-pdf-html': ['html', 'htm', 'xhtml'],
  'to-pdf-markdown': ['md', 'markdown'],
}

/** Which Convert-to-PDF tool handles this file, if any. */
export function convertToolFor(path: string): ToolId | null {
  const ext = extOf(path)
  const hit = Object.entries(CONVERT_EXTS).find(([, exts]) => exts.includes(ext))
  return hit ? (hit[0] as ToolId) : null
}
