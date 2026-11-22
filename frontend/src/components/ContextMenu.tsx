import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

export type MenuItem = { label: string; onSelect: () => void; disabled?: boolean } | 'separator'

export interface MenuState {
  x: number
  y: number
  items: MenuItem[]
}

const EDGE = 8

export function ContextMenu({ menu, onClose }: { menu: MenuState; onClose: () => void }) {
  const ref = useRef<HTMLDivElement>(null)
  const [pos, setPos] = useState({ left: menu.x, top: menu.y })

  // Keep the menu inside the window, then focus the first item for keyboard use.
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    const { width, height } = el.getBoundingClientRect()
    setPos({
      left: Math.max(EDGE, Math.min(menu.x, window.innerWidth - width - EDGE)),
      top: Math.max(EDGE, Math.min(menu.y, window.innerHeight - height - EDGE)),
    })
    el.querySelector<HTMLButtonElement>('button:not(:disabled)')?.focus()
  }, [menu])

  useEffect(() => {
    const onPointer = (e: PointerEvent) => {
      if (!ref.current?.contains(e.target as Node)) onClose()
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('pointerdown', onPointer, true)
    window.addEventListener('keydown', onKey)
    window.addEventListener('blur', onClose)
    window.addEventListener('resize', onClose)
    return () => {
      window.removeEventListener('pointerdown', onPointer, true)
      window.removeEventListener('keydown', onKey)
      window.removeEventListener('blur', onClose)
      window.removeEventListener('resize', onClose)
    }
  }, [onClose])

  function moveFocus(delta: number) {
    const buttons = [...(ref.current?.querySelectorAll<HTMLButtonElement>('button:not(:disabled)') ?? [])]
    const i = buttons.indexOf(document.activeElement as HTMLButtonElement)
    buttons[(i + delta + buttons.length) % buttons.length]?.focus()
  }

  // Rendered at the top level: inside a frosted panel, `position: fixed` would be relative
  // to the panel (backdrop-filter makes it the containing block) and clipped by it.
  return createPortal(
    <div
      ref={ref}
      className="menu"
      role="menu"
      style={pos}
      onContextMenu={(e) => e.preventDefault()}
      onKeyDown={(e) => {
        if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
          e.preventDefault()
          moveFocus(e.key === 'ArrowDown' ? 1 : -1)
        }
      }}
    >
      {menu.items.map((item, i) =>
        item === 'separator' ? (
          <div key={`sep-${i}`} className="menu-sep" role="separator" />
        ) : (
          <button
            key={item.label}
            type="button"
            role="menuitem"
            className="menu-item"
            disabled={item.disabled}
            onClick={() => {
              onClose()
              item.onSelect()
            }}
          >
            {item.label}
          </button>
        ),
      )}
    </div>,
    document.body,
  )
}
