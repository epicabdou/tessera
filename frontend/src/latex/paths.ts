/** Path of `target` relative to the folder `fromDir`, with forward slashes, as \includegraphics wants it. */
export function relativeTexPath(fromDir: string, target: string): string {
  const split = (p: string) => p.replace(/\//g, '\\').replace(/\\+$/, '').split('\\')
  const a = split(fromDir)
  const b = split(target)
  // Different drives: no relative path exists.
  if (a[0].toLowerCase() !== b[0].toLowerCase()) return b.join('/')
  let i = 0
  while (i < a.length && i < b.length - 1 && a[i].toLowerCase() === b[i].toLowerCase()) i++
  const up = a.length - i
  return [...Array(up).fill('..'), ...b.slice(i)].join('/')
}
