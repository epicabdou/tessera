/** Join class names, skipping falsy values. */
export function cls(...names: (string | false | null | undefined)[]): string {
  return names.filter(Boolean).join(' ')
}
