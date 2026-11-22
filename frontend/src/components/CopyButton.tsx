import { useEffect, useState } from 'react'

export function CopyButton({ value, label = 'Copy' }: { value: string; label?: string }) {
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!copied) return
    const t = window.setTimeout(() => setCopied(false), 1400)
    return () => window.clearTimeout(t)
  }, [copied])

  return (
    <button
      type="button"
      className="btn btn-ghost btn-sm"
      disabled={!value}
      onClick={async () => {
        await navigator.clipboard.writeText(value)
        setCopied(true)
      }}
    >
      {copied ? 'Copied' : label}
    </button>
  )
}
