import { useEffect, useState } from 'react'
import { ErrorNotice } from '../components/ErrorNotice'
import { call, toError, type SecurityInfo } from '../lib/bridge'
import { formatBytes } from '../lib/format'
import { ResultCard } from '../pdf/components'
import { useSaveFlow } from '../pdf/useSaveFlow'
import { PathGate } from './PathGate'

const PERMS: { id: string; label: string }[] = [
  { id: 'print', label: 'Printing' },
  { id: 'print_high', label: 'High-quality printing' },
  { id: 'copy', label: 'Copying text and images' },
  { id: 'modify', label: 'Editing the content' },
  { id: 'annotate', label: 'Comments and annotations' },
  { id: 'fill_forms', label: 'Filling in forms' },
  { id: 'assemble', label: 'Inserting, deleting and rotating pages' },
  { id: 'accessibility', label: 'Text access for screen readers' },
]

export function ProtectPdf() {
  return (
    <section className="tool">
      <header className="tool-header">
        <h1>Protect PDF</h1>
        <p>Encrypt a PDF with a password, restrict printing, copying or editing — or remove a protection you know the password for.</p>
      </header>
      <PathGate tool="protect-pdf">{(path, reopen) => <ProtectBody path={path} reopen={reopen} />}</PathGate>
    </section>
  )
}

function ProtectBody({ path, reopen }: { path: string; reopen: (path: string) => void }) {
  const [info, setInfo] = useState<SecurityInfo | null>(null)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    call('pdf_security_info', path).then(setInfo, (err) => setError(toError(err)))
  }, [path])

  if (error) return <ErrorNotice error={error} />
  if (!info) return <p className="muted">Reading…</p>
  return info.encrypted ? <UnlockForm info={info} reopen={reopen} /> : <ProtectForm info={info} reopen={reopen} />
}

function ProtectForm({ info, reopen }: { info: SecurityInfo; reopen: (path: string) => void }) {
  const flow = useSaveFlow()
  const [openPw, setOpenPw] = useState('')
  const [confirm, setConfirm] = useState('')
  const [ownerPw, setOwnerPw] = useState('')
  const [show, setShow] = useState(false)
  const [allowed, setAllowed] = useState<Record<string, boolean>>(() => Object.fromEntries(PERMS.map((p) => [p.id, true])))
  const [algorithm, setAlgorithm] = useState('AES-256')
  const restricted = Object.values(allowed).some((v) => !v)
  const mismatch = openPw !== '' && confirm !== openPw
  const sameAsOwner = openPw !== '' && ownerPw === openPw
  const canSave = !mismatch && !sameAsOwner && (openPw !== '' || restricted)
  const type = show ? 'text' : 'password'

  return (
    <>
      <p className="small muted">
        Not protected · {info.page_count ?? '?'} pages · {formatBytes(info.size)}
      </p>
      <div className="card conv-options">
        <h2 className="panel-title">Password to open</h2>
        <div className="opt-grid">
          <label>
            Open password
            <input className="text-input" type={type} value={openPw} autoComplete="new-password" onChange={(e) => setOpenPw(e.target.value)} placeholder="Leave empty to allow opening without one" />
          </label>
          <label>
            Confirm
            <input className="text-input" type={type} value={confirm} autoComplete="new-password" aria-invalid={mismatch} onChange={(e) => setConfirm(e.target.value)} disabled={!openPw} />
            {mismatch && <span className="field-error small">The passwords don’t match</span>}
          </label>
          <label className="check span-2">
            <input type="checkbox" checked={show} onChange={(e) => setShow(e.target.checked)} /> Show passwords
          </label>
        </div>
      </div>
      <div className="card conv-options">
        <h2 className="panel-title">Restrictions</h2>
        <p className="muted small">Untick what readers may not do. PDF readers honour these restrictions; they are not a strong barrier on their own.</p>
        <div className="perm-grid">
          {PERMS.map((p) => (
            <label key={p.id} className="check">
              <input type="checkbox" checked={allowed[p.id]} onChange={(e) => setAllowed((a) => ({ ...a, [p.id]: e.target.checked }))} /> {p.label}
            </label>
          ))}
        </div>
        <div className="opt-grid">
          <label>
            Permissions password
            <input className="text-input" type={type} value={ownerPw} autoComplete="new-password" aria-invalid={sameAsOwner} onChange={(e) => setOwnerPw(e.target.value)} placeholder="Generated if empty" />
            {sameAsOwner && <span className="field-error small">Use a different password from the open password</span>}
          </label>
          <label>
            Encryption
            <select className="text-input" value={algorithm} onChange={(e) => setAlgorithm(e.target.value)}>
              <option value="AES-256">AES 256-bit (recommended)</option>
              <option value="AES-128">AES 128-bit (Acrobat 7+)</option>
              <option value="RC4-128">RC4 128-bit (old readers)</option>
            </select>
          </label>
        </div>
      </div>
      <ErrorNotice error={flow.error} />
      {flow.saved && <ResultCard files={flow.saved} onDismiss={flow.dismiss} onContinue={(f) => reopen(f.path)} />}
      <div className="action-bar">
        <span className="muted small">{!openPw && !restricted ? 'Set an open password or untick a permission.' : ''}</span>
        <button
          type="button"
          className="btn btn-primary"
          disabled={flow.busy || !canSave}
          onClick={() => flow.saveAs(info.path, 'protected', (out) => call('pdf_protect', info.path, out, openPw, ownerPw, allowed, algorithm))}
        >
          {flow.busy ? 'Encrypting…' : 'Protect and save…'}
        </button>
      </div>
    </>
  )
}

function UnlockForm({ info, reopen }: { info: SecurityInfo; reopen: (path: string) => void }) {
  const flow = useSaveFlow()
  const [password, setPassword] = useState('')
  const denied = PERMS.filter((p) => info.permissions[p.id] === false)

  return (
    <>
      <div className="card">
        <p>
          <strong>This PDF is protected.</strong>{' '}
          {info.needs_password ? 'It needs a password to open.' : 'It opens without a password but has restrictions.'}
        </p>
        {denied.length > 0 && <p className="small muted">Not allowed: {denied.map((p) => p.label.toLowerCase()).join(', ')}.</p>}
      </div>
      <div className="card conv-options">
        <h2 className="panel-title">Remove the protection</h2>
        <label>
          {info.needs_password ? 'Open or permissions password' : 'Permissions password (if the file has one)'}
          <input className="text-input" type="password" autoComplete="off" value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        <p className="muted small">Only remove protection from documents you own or are allowed to change.</p>
      </div>
      <ErrorNotice error={flow.error} />
      {flow.saved && <ResultCard files={flow.saved} onDismiss={flow.dismiss} onContinue={(f) => reopen(f.path)} />}
      <div className="action-bar">
        <span />
        <button
          type="button"
          className="btn btn-primary"
          disabled={flow.busy || (info.needs_password && !password)}
          onClick={() => flow.saveAs(info.path, 'unlocked', (out) => call('pdf_unlock', info.path, out, password))}
        >
          {flow.busy ? 'Unlocking…' : 'Unlock and save…'}
        </button>
      </div>
    </>
  )
}
