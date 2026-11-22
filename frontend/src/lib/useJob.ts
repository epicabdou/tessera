import { useCallback, useState } from 'react'
import { call, type JobProgress } from './bridge'

/**
 * Run a long Python call and poll its progress. The Python method takes a job id
 * and reports through services/progress.py; `progress` updates a few times a second.
 */
export function useJob() {
  const [busy, setBusy] = useState(false)
  const [progress, setProgress] = useState<JobProgress | null>(null)

  const run = useCallback(async <T>(work: (jobId: string) => Promise<T>): Promise<T> => {
    const id = `job-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    setBusy(true)
    setProgress(null)
    const timer = window.setInterval(() => {
      call('job_progress', id).then((p) => p && setProgress(p), () => {})
    }, 350)
    try {
      return await work(id)
    } finally {
      window.clearInterval(timer)
      setBusy(false)
      setProgress(null)
    }
  }, [])

  return { busy, progress, run }
}
