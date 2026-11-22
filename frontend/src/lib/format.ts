export function formatBytes(n: number): string {
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let i = 0
  let v = n
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024
    i++
  }
  return `${i === 0 ? v : v.toFixed(1)} ${units[i]}`
}

const dateFormat = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })

/** `seconds` since the epoch, as Python's os.stat returns it. */
export function formatDate(seconds: number): string {
  return dateFormat.format(new Date(seconds * 1000))
}

/** [0,1,2,4] -> "1-3, 5" (1-based), the same format the Python side parses. */
export function formatRanges(indexes: Iterable<number>): string {
  const sorted = [...new Set(indexes)].sort((a, b) => a - b)
  const parts: string[] = []
  for (let i = 0; i < sorted.length; ) {
    let j = i
    while (j + 1 < sorted.length && sorted[j + 1] === sorted[j] + 1) j++
    parts.push(i === j ? `${sorted[i] + 1}` : `${sorted[i] + 1}-${sorted[j] + 1}`)
    i = j + 1
  }
  return parts.join(', ')
}

export function dirname(path: string): string {
  return path.replace(/[\\/][^\\/]*$/, '') || path
}

export const MM_PER_POINT = 25.4 / 72

/** Path equality that ignores case for Windows-style paths. */
export function samePath(a: string | null | undefined, b: string | null | undefined): boolean {
  if (!a || !b) return false
  const windows = /^[a-z]:[\\/]|^\\\\/i.test(a)
  return windows ? a.toLowerCase() === b.toLowerCase() : a === b
}
