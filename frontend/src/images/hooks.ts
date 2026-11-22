import { useCallback, useEffect, useRef, useState } from 'react'
import { call, toError, type ImageInfo, type ImageThumb } from '../lib/bridge'
import { extOf, IMAGE_EXTS, useToolRequest, type ToolId } from '../lib/workspace'
import { loadPreview } from './context'

/** `value`, updated only after it has stayed the same for `ms`. */
export function useDebounced<T>(value: T, ms = 300): T {
  const [settled, setSettled] = useState(value)
  useEffect(() => {
    const t = window.setTimeout(() => setSettled(value), ms)
    return () => window.clearTimeout(t)
  }, [value, ms])
  return settled
}

/** Preview data URL for the open image (null while loading). */
export function useImagePreview(image: ImageInfo | null, maxSide = 1600) {
  const [url, setUrl] = useState<string | null>(null)
  const [error, setError] = useState<Error | null>(null)
  useEffect(() => {
    if (!image) return
    let active = true
    loadPreview(image.path, image.mtime, maxSide).then(
      (p) => active && setUrl(p.data_url),
      (err) => active && setError(toError(err)),
    )
    return () => {
      active = false
    }
  }, [image, maxSide])
  return { url: image ? url : null, error }
}

/**
 * Live preview rendered by Python (what you see is what you get). `render` is re-run,
 * debounced, whenever `key` changes; results that arrive out of order are dropped.
 */
export function useRendered<T>(key: string | null, render: () => Promise<T>, ms = 250) {
  const [result, setResult] = useState<T | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const latest = useRef(render)
  const seq = useRef(0)
  useEffect(() => {
    latest.current = render
  })
  useEffect(() => {
    if (key === null) return
    const n = ++seq.current
    const t = window.setTimeout(() => {
      setBusy(true)
      latest.current().then(
        (r) => {
          if (n !== seq.current) return
          setResult(r)
          setError(null)
          setBusy(false)
        },
        (err) => {
          if (n !== seq.current) return
          setError(toError(err))
          setBusy(false)
        },
      )
    }, ms)
    return () => window.clearTimeout(t)
  }, [key, ms])
  return { result, busy, error }
}

export interface ListItem extends ImageThumb {
  /** Clockwise quarter turns (Rotate). */
  turns?: number
  flipH?: boolean
  flipV?: boolean
}

/** The file list of a batch image tool: add (dialog, Explorer drop, "open in"), remove, reorder. */
export function useImageList(tool: ToolId, accept: string[] = IMAGE_EXTS) {
  const [items, setItems] = useState<ListItem[]>([])
  const [error, setError] = useState<Error | null>(null)
  const acceptRef = useRef(accept)

  const add = useCallback(async (paths: string[]) => {
    const wanted = paths.filter((p) => acceptRef.current.includes(extOf(p)))
    if (!wanted.length) {
      if (paths.length) setError(new Error(`This tool takes ${acceptRef.current.filter((e) => e !== 'jfif').join(', ').toUpperCase()} images`))
      return
    }
    setError(null)
    try {
      const thumbs = await call('image_thumbnails', wanted, 160)
      setItems((list) => {
        const have = new Set(list.map((i) => i.path.toLowerCase()))
        return [...list, ...thumbs.filter((t) => !have.has(t.path.toLowerCase()))]
      })
    } catch (err) {
      setError(toError(err))
    }
  }, [])

  useToolRequest(tool, (path) => void add([path]))

  const pick = useCallback(async () => {
    try {
      const paths = await call('pick_files', 'Images', acceptRef.current, true)
      if (paths.length) await add(paths)
    } catch (err) {
      setError(toError(err))
    }
  }, [add])

  const remove = useCallback((path: string) => setItems((list) => list.filter((i) => i.path !== path)), [])
  const update = useCallback((path: string, patch: Partial<ListItem>) => setItems((list) => list.map((i) => (i.path === path ? { ...i, ...patch } : i))), [])
  const clear = useCallback(() => setItems([]), [])
  const good = items.filter((i) => !i.error)

  return { items, good, add, pick, remove, update, clear, setItems, error, setError }
}
