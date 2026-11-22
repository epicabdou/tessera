import { useState, type DragEvent } from 'react'
import { DND_FILE } from '../browser/fileKinds'
import type { WebPrintOptions } from '../lib/bridge'

export const DEFAULT_PRINT: WebPrintOptions = {
  page_size: 'a4',
  orientation: 'portrait',
  margin: 'normal',
  scale: 100,
  backgrounds: true,
  header_footer: false,
  wait: 0,
  scroll: true,
}

export const basename = (path: string) => path.split(/[\\/]/).pop() ?? path
export const stem = (path: string) => basename(path).replace(/\.[^.]+$/, '')

/** A file name hint from a web address: "example.com/docs/page.html" -> "example.com-docs-page". */
export function hostHint(text: string): string {
  try {
    const u = new URL(/^[a-z]+:\/\//i.test(text) ? text : `https://${text}`)
    return u.hostname + (u.pathname.length > 1 ? u.pathname.replace(/\.[a-z]+$/i, '').replace(/[/]+/g, '-') : '')
  } catch {
    return 'web-page'
  }
}

/** Drop target for files dragged from the Explorer. */
export function useFileDrop(onPaths: (paths: string[]) => void) {
  const [over, setOver] = useState(false)
  const accepts = (e: DragEvent) => e.dataTransfer.types.includes(DND_FILE)
  return {
    over,
    props: {
      onDragOver: (e: DragEvent) => {
        if (!accepts(e)) return
        e.preventDefault()
        setOver(true)
      },
      onDragLeave: (e: DragEvent) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setOver(false)
      },
      onDrop: (e: DragEvent) => {
        setOver(false)
        if (!accepts(e)) return
        e.preventDefault()
        onPaths([e.dataTransfer.getData(DND_FILE)])
      },
    },
  }
}
