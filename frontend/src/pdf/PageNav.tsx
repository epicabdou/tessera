import { IconButton } from '../components/IconButton'
import { ArrowLeftIcon, ArrowRightIcon } from '../components/icons'

/** ‹ Page 3 of 12 › */
export function PageNav({ index, count, onChange }: { index: number; count: number; onChange: (index: number) => void }) {
  return (
    <div className="page-nav">
      <IconButton label="Previous page" disabled={index === 0} onClick={() => onChange(index - 1)}>
        <ArrowLeftIcon size={15} />
      </IconButton>
      <span>
        Page{' '}
        <input
          className="text-input num tiny"
          type="number"
          min={1}
          max={count}
          value={index + 1}
          aria-label="Page"
          onChange={(e) => {
            const n = Number(e.target.value)
            if (n >= 1 && n <= count) onChange(n - 1)
          }}
        />{' '}
        of {count}
      </span>
      <IconButton label="Next page" disabled={index >= count - 1} onClick={() => onChange(index + 1)}>
        <ArrowRightIcon size={15} />
      </IconButton>
    </div>
  )
}
