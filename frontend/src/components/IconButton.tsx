import type { ReactNode } from 'react'
import { cls } from '../lib/cls'

interface Props {
  label: string
  onClick: () => void
  children: ReactNode
  disabled?: boolean
  active?: boolean
}

export function IconButton({ label, onClick, children, disabled, active }: Props) {
  return (
    <button
      type="button"
      className={cls('icon-btn', active && 'is-on')}
      title={label}
      aria-label={label}
      aria-pressed={active}
      disabled={disabled}
      onClick={onClick}
    >
      {children}
    </button>
  )
}
