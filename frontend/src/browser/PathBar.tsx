import { Fragment, useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import { IconButton } from '../components/IconButton'
import { ArrowLeftIcon, ArrowRightIcon, ArrowUpIcon } from '../components/icons'
import { toError, type DirListing } from '../lib/bridge'

interface Props {
  root: string | null
  listing: DirListing | undefined
  canBack: boolean
  canForward: boolean
  onBack: () => void
  onForward: () => void
  onUp: () => void
  /** Navigate to typed text; rejects with a message if it isn't a folder. */
  onSubmitPath: (text: string) => Promise<void>
  onCrumb: (path: string) => void
  trailing?: ReactNode
}

/** Back / Forward / Up, clickable breadcrumbs, and an editable path (click the bar or Ctrl+L). */
export function PathBar({ root, listing, canBack, canForward, onBack, onForward, onUp, onSubmitPath, onCrumb, trailing }: Props) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')
  const [error, setError] = useState<string | null>(null)
  const crumbsRef = useRef<HTMLDivElement>(null)

  // Long paths: keep the current folder (the end) in view.
  useLayoutEffect(() => {
    const el = crumbsRef.current
    if (el) el.scrollLeft = el.scrollWidth
  }, [listing?.path, editing])

  function startEditing() {
    setDraft(root ?? '')
    setError(null)
    setEditing(true)
  }

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key.toLowerCase() === 'l') {
        e.preventDefault()
        setDraft(root ?? '')
        setError(null)
        setEditing(true)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [root])

  async function submit() {
    try {
      await onSubmitPath(draft)
      setEditing(false)
      setError(null)
    } catch (err) {
      setError(toError(err).message)
    }
  }

  return (
    <div className="pathbar-wrap">
      <div className="pathbar">
        <IconButton label="Back (Alt+Left)" disabled={!canBack} onClick={onBack}>
          <ArrowLeftIcon size={15} />
        </IconButton>
        <IconButton label="Forward (Alt+Right)" disabled={!canForward} onClick={onForward}>
          <ArrowRightIcon size={15} />
        </IconButton>
        <IconButton label="Up one level (Backspace)" disabled={!listing?.parent} onClick={onUp}>
          <ArrowUpIcon size={15} />
        </IconButton>

        {editing ? (
          <input
            className="path-input"
            autoFocus
            value={draft}
            spellCheck={false}
            aria-label="Folder path"
            aria-invalid={error !== null}
            onFocus={(e) => e.currentTarget.select()}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={() => {
              setEditing(false)
              setError(null)
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter') void submit()
              if (e.key === 'Escape') {
                setEditing(false)
                setError(null)
              }
            }}
          />
        ) : (
          <div ref={crumbsRef} className="crumbs" title="Click to type a path (Ctrl+L)" onClick={startEditing}>
            {listing?.crumbs.map((c, i) => (
              <Fragment key={c.path}>
                {i > 0 && <span className="crumb-sep">›</span>}
                <button
                  type="button"
                  className="crumb"
                  onClick={(e) => {
                    e.stopPropagation()
                    onCrumb(c.path)
                  }}
                >
                  {c.name}
                </button>
              </Fragment>
            ))}
            <span className="crumbs-fill" />
          </div>
        )}
        {trailing}
      </div>
      {error && <div className="path-error">{error}</div>}
    </div>
  )
}
