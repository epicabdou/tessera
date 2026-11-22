import { useCallback, useState } from 'react'
import { call, toError, type SavedFile } from '../lib/bridge'
import { useWorkspace } from '../lib/workspace'

/**
 * Save flow shared by the PDF tools: native Save dialog (pre-filled with a
 * non-clashing "<name>_<suffix>.pdf"), run the operation, show the result,
 * and tell the Explorer something changed.
 */
export function useSaveFlow() {
  const { filesChanged } = useWorkspace()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const [saved, setSaved] = useState<SavedFile[] | null>(null)

  /** Save dialog pre-filled with `suggest()`, then `run(chosenPath)`. `type` picks a non-PDF file type. */
  const saveTo = useCallback(
    async (
      suggest: () => Promise<string>,
      run: (output: string) => Promise<SavedFile>,
      type?: { label: string; extensions: string[] },
    ) => {
      setError(null)
      try {
        const suggested = await suggest()
        const output = type
          ? await call('save_file_dialog', suggested, type.label, type.extensions)
          : await call('save_pdf_dialog', suggested)
        if (!output) return null
        setBusy(true)
        const result = await run(output)
        setSaved([result])
        filesChanged()
        return result
      } catch (err) {
        setError(toError(err))
        return null
      } finally {
        setBusy(false)
      }
    },
    [filesChanged],
  )

  /** Save dialog pre-filled with "<source name>_<suffix>.pdf". */
  const saveAs = useCallback(
    (source: string, suffix: string, run: (output: string) => Promise<SavedFile>) =>
      saveTo(() => call('pdf_suggest_output', source, suffix), run),
    [saveTo],
  )

  const saveToFolder = useCallback(
    async (defaultDir: string, run: (folder: string) => Promise<SavedFile[]>) => {
      setError(null)
      try {
        const folder = await call('pick_folder', defaultDir)
        if (!folder) return null
        setBusy(true)
        const files = await run(folder)
        setSaved(files)
        filesChanged()
        return files
      } catch (err) {
        setError(toError(err))
        return null
      } finally {
        setBusy(false)
      }
    },
    [filesChanged],
  )

  /** Run a save that needs no dialog (e.g. "next to each file"). */
  const runSave = useCallback(
    async (run: () => Promise<SavedFile[]>) => {
      setError(null)
      try {
        setBusy(true)
        const files = await run()
        setSaved(files)
        filesChanged()
        return files
      } catch (err) {
        setError(toError(err))
        return null
      } finally {
        setBusy(false)
      }
    },
    [filesChanged],
  )

  const reset = useCallback(() => {
    setSaved(null)
    setError(null)
  }, [])

  return { busy, error, saved, saveAs, saveTo, saveToFolder, runSave, setError, dismiss: () => setSaved(null), reset }
}
