import { createContext, useContext } from 'react'
import { call, type ImageFormat, type ImageInfo, type ImageView } from '../lib/bridge'

/** The image that Crop, Upscale, Remove background, Blur faces and the Photo editor share. */
export interface ImageDocState {
  image: ImageInfo | null
  loading: boolean
  error: string | null
  open(path: string): Promise<boolean>
  pick(): Promise<void>
  close(): void
}

export const ImageDocContext = createContext<ImageDocState | null>(null)

export function useImageDoc(): ImageDocState {
  const state = useContext(ImageDocContext)
  if (!state) throw new Error('useImageDoc must be used inside ImageDocProvider')
  return state
}

const previews = new Map<string, Promise<ImageView>>()

/** Upright preview of a file version (cached; a few large previews at most). */
export function loadPreview(path: string, mtime: number, maxSide: number): Promise<ImageView> {
  const key = `${path}|${mtime}|${maxSide}`
  let hit = previews.get(key)
  if (!hit) {
    hit = call('image_preview', path, maxSide)
    hit.catch(() => previews.delete(key))
    previews.set(key, hit)
    if (previews.size > 24) previews.delete(previews.keys().next().value as string)
  }
  return hit
}

export const formatBytesShort = (n: number) => (n < 1024 ? `${n} B` : n < 1024 ** 2 ? `${(n / 1024).toFixed(0)} KB` : `${(n / 1024 ** 2).toFixed(1)} MB`)

export const FORMAT_LABELS: Record<ImageFormat, string> = {
  jpg: 'JPG',
  png: 'PNG',
  webp: 'WebP',
  avif: 'AVIF',
  gif: 'GIF',
  bmp: 'BMP',
  tiff: 'TIFF',
}

/** Extension a saved image gets for `fmt` ("keep" follows the source; HEIC/ICO aren't written). */
export function outputExt(path: string, fmt: string): string {
  if (fmt !== 'keep') return fmt === 'tiff' ? 'tif' : fmt
  const ext = (path.match(/\.([^.\\/]+)$/)?.[1] ?? '').toLowerCase()
  if (['jpg', 'jpeg', 'jfif', 'heic', 'heif'].includes(ext)) return 'jpg'
  if (ext === 'ico') return 'png'
  if (ext === 'tiff') return 'tif'
  return ext || 'png'
}
