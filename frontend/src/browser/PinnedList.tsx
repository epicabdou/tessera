import { useRef, useState, type DragEvent, type MouseEvent } from 'react'
import { PinIcon } from '../components/icons'
import type { PinnedFolder } from '../lib/bridge'
import { cls } from '../lib/cls'
import { samePath } from '../lib/format'
import { DND_PATH } from './fileKinds'

interface Props {
  pins: PinnedFolder[]
  activeRoot: string | null
  onOpen: (pin: PinnedFolder) => void
  /** Pin `path` at `index`, or move it there if it's already pinned. */
  onPinAt: (path: string, index: number) => void
  onMenu: (e: MouseEvent, pin: PinnedFolder, index: number) => void
}

/** Pinned folders. Drag to reorder; drop a folder from the tree to pin it. */
export function PinnedList({ pins, activeRoot, onOpen, onPinAt, onMenu }: Props) {
  const listRef = useRef<HTMLUListElement>(null)
  const [dropSlot, setDropSlot] = useState<number | null>(null)

  const accepts = (e: DragEvent) => e.dataTransfer.types.includes(DND_PATH)

  // Slot n means "before pin n"; pins.length means "at the end".
  function slotAt(e: DragEvent): number {
    const items = listRef.current?.querySelectorAll<HTMLElement>('[data-pin-index]') ?? []
    for (const el of items) {
      const r = el.getBoundingClientRect()
      if (e.clientY < r.top + r.height / 2) return Number(el.dataset.pinIndex)
    }
    return pins.length
  }

  function onDrop(e: DragEvent) {
    if (!accepts(e)) return
    e.preventDefault()
    const path = e.dataTransfer.getData(DND_PATH)
    const slot = slotAt(e)
    setDropSlot(null)
    const from = pins.findIndex((p) => samePath(p.path, path))
    // Removing the item first shifts later slots up by one.
    const to = from !== -1 && slot > from ? slot - 1 : slot
    if (path && from !== to) onPinAt(path, to)
  }

  return (
    <ul
      ref={listRef}
      className={cls('nav-list', 'pinned-list', dropSlot !== null && 'is-drop-target')}
      onDragOver={(e) => {
        if (!accepts(e)) return
        e.preventDefault()
        e.dataTransfer.dropEffect = 'move'
        setDropSlot(slotAt(e))
      }}
      onDragLeave={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setDropSlot(null)
      }}
      onDrop={onDrop}
    >
      {pins.length === 0 && <li className="empty-hint">Drag a folder here, or right-click one and choose Pin.</li>}
      {pins.map((pin, i) => (
        <li key={pin.path} data-pin-index={i} className={cls(dropSlot === i && 'drop-before')}>
          <button
            type="button"
            className={cls('nav-row', samePath(pin.path, activeRoot) && 'is-active', !pin.exists && 'is-missing')}
            title={pin.exists ? pin.path : `${pin.path}\nFolder not found`}
            draggable
            onDragStart={(e) => {
              e.dataTransfer.setData(DND_PATH, pin.path)
              e.dataTransfer.effectAllowed = 'move'
            }}
            onDragEnd={() => setDropSlot(null)}
            onClick={() => onOpen(pin)}
            onContextMenu={(e) => {
              e.preventDefault()
              e.stopPropagation()
              onMenu(e, pin, i)
            }}
          >
            <PinIcon size={15} className="nav-icon" />
            <span className="nav-label">{pin.name}</span>
          </button>
        </li>
      ))}
      {pins.length > 0 && dropSlot === pins.length && <li className="drop-end" aria-hidden="true" />}
    </ul>
  )
}
