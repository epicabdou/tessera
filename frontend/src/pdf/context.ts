import { createContext, useContext } from 'react'
import type { PdfInfo } from '../lib/bridge'

/** Identifies a version of a file: previews are cached per (path, mtime). */
export interface FileRef {
  path: string
  mtime: number
}

export interface ThumbStore {
  get(file: FileRef, index: number, width: number): string | undefined
  /** Queue a page preview; requests made in the same tick go to Python in one batch. */
  request(file: FileRef, index: number, width: number): void
  /** Bumps when new previews arrive. */
  version: number
}

export const ThumbContext = createContext<ThumbStore | null>(null)

export function useThumbStore(): ThumbStore {
  const store = useContext(ThumbContext)
  if (!store) throw new Error('useThumbStore must be used inside ThumbProvider')
  return store
}

/** The PDF that Split, Organize, Rotate, Crop and Page numbers share. */
export interface PdfDocState {
  doc: PdfInfo | null
  loading: boolean
  error: string | null
  open(path: string): Promise<boolean>
  pick(): Promise<void>
  close(): void
}

export const PdfDocContext = createContext<PdfDocState | null>(null)

export function usePdfDoc(): PdfDocState {
  const state = useContext(PdfDocContext)
  if (!state) throw new Error('usePdfDoc must be used inside PdfDocProvider')
  return state
}
