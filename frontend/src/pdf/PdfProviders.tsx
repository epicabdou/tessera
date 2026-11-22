import { useCallback, useMemo, useRef, useState, type ReactNode } from 'react'
import { call, toError, type PdfInfo } from '../lib/bridge'
import { PdfDocContext, ThumbContext, type FileRef, type PdfDocState, type ThumbStore } from './context'

const BATCH = 6
const MAX_RETRIES = 2
const RETRY_MS = 600

const keyOf = (file: FileRef, width: number, index: number) => `${file.path}|${file.mtime}|${width}|${index}`

export function ThumbProvider({ children }: { children: ReactNode }) {
  const cache = useRef(new Map<string, string>())
  const known = useRef(new Set<string>()) // requested (in flight, done or failed)
  const failures = useRef(new Map<string, number>())
  const pending = useRef(new Map<string, { file: FileRef; width: number; indexes: number[] }>())
  const timer = useRef<number | null>(null)
  const [version, setVersion] = useState(0)

  const flush = useCallback(() => {
    timer.current = null
    const batches = [...pending.current.values()]
    pending.current.clear()
    for (const { file, width, indexes } of batches) {
      for (let k = 0; k < indexes.length; k += BATCH) {
        const chunk = indexes.slice(k, k + BATCH)
        call('pdf_thumbnails', file.path, chunk, width).then(
          (urls) => {
            urls.forEach((url, j) => url && cache.current.set(keyOf(file, width, chunk[j]), url))
            setVersion((v) => v + 1)
          },
          () => {
            // A transient failure (file briefly locked, still being written): let the
            // pages ask again a couple of times; after that they simply stay blank.
            const keys = chunk.map((i) => keyOf(file, width, i)).filter((k) => (failures.current.get(k) ?? 0) < MAX_RETRIES)
            if (!keys.length) return
            keys.forEach((k) => failures.current.set(k, (failures.current.get(k) ?? 0) + 1))
            window.setTimeout(() => {
              keys.forEach((k) => known.current.delete(k))
              setVersion((v) => v + 1)
            }, RETRY_MS)
          },
        )
      }
    }
  }, [])

  const request = useCallback(
    (file: FileRef, index: number, width: number) => {
      const key = keyOf(file, width, index)
      if (known.current.has(key)) return
      known.current.add(key)
      const batchKey = `${file.path}|${file.mtime}|${width}`
      const batch = pending.current.get(batchKey) ?? { file, width, indexes: [] }
      batch.indexes.push(index)
      pending.current.set(batchKey, batch)
      timer.current ??= window.setTimeout(flush, 16)
    },
    [flush],
  )

  const get = useCallback((file: FileRef, index: number, width: number) => cache.current.get(keyOf(file, width, index)), [])

  const value = useMemo<ThumbStore>(() => ({ get, request, version }), [get, request, version])
  return <ThumbContext.Provider value={value}>{children}</ThumbContext.Provider>
}

export function PdfDocProvider({ children }: { children: ReactNode }) {
  const [doc, setDoc] = useState<PdfInfo | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const open = useCallback(async (path: string) => {
    setLoading(true)
    setError(null)
    try {
      setDoc(await call('pdf_info', path))
      return true
    } catch (err) {
      setError(toError(err).message)
      return false
    } finally {
      setLoading(false)
    }
  }, [])

  const pick = useCallback(async () => {
    try {
      const [path] = await call('pick_pdfs', false)
      if (path) await open(path)
    } catch (err) {
      setError(toError(err).message)
    }
  }, [open])

  const close = useCallback(() => {
    setDoc(null)
    setError(null)
  }, [])

  const value = useMemo<PdfDocState>(() => ({ doc, loading, error, open, pick, close }), [doc, loading, error, open, pick, close])
  return <PdfDocContext.Provider value={value}>{children}</PdfDocContext.Provider>
}
