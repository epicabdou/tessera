export function ErrorNotice({ error }: { error: Error | null }) {
  if (!error) return null
  return (
    <div className="notice notice-error" role="alert">
      {error.message}
    </div>
  )
}
