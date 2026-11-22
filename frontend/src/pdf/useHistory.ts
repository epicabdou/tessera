import { useCallback, useState } from 'react'

const LIMIT = 100

/** Value with undo/redo. `set` takes an updater; returning the same value records nothing. */
export function useHistory<T>(init: () => T) {
  const [state, setState] = useState(() => ({ past: [] as T[], present: init(), future: [] as T[] }))

  const set = useCallback(
    (update: (prev: T) => T) =>
      setState((s) => {
        const next = update(s.present)
        return next === s.present ? s : { past: [...s.past.slice(-LIMIT + 1), s.present], present: next, future: [] }
      }),
    [],
  )

  const undo = useCallback(
    () =>
      setState((s) =>
        s.past.length ? { past: s.past.slice(0, -1), present: s.past[s.past.length - 1], future: [s.present, ...s.future] } : s,
      ),
    [],
  )

  const redo = useCallback(
    () => setState((s) => (s.future.length ? { past: [...s.past, s.present], present: s.future[0], future: s.future.slice(1) } : s)),
    [],
  )

  const reset = useCallback((value: T) => setState({ past: [], present: value, future: [] }), [])

  return {
    value: state.present,
    set,
    undo,
    redo,
    reset,
    canUndo: state.past.length > 0,
    canRedo: state.future.length > 0,
  }
}
