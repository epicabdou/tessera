import { useCallback, useEffect, useState } from 'react'
import { ErrorNotice } from '../components/ErrorNotice'
import { call, toError, type CertInfo, type PdfInfo, type SignatureStatus } from '../lib/bridge'
import { cls } from '../lib/cls'
import { useToolRequest } from '../lib/workspace'
import { BoxLayer, type Rect } from '../editing/BoxLayer'
import { newId, objectContent, toPayload, type EditObj } from '../editing/objects'
import { DocGate, PagePreview, ResultCard } from '../pdf/components'
import { usePdfDoc } from '../pdf/context'
import { PageNav } from '../pdf/PageNav'
import { useSaveFlow } from '../pdf/useSaveFlow'
import { SignaturePad, type Signature } from './SignaturePad'

const CERT_KEY = 'toolbox.signCertificate'

function rememberedCert(): string {
  try {
    return localStorage.getItem(CERT_KEY) ?? ''
  } catch {
    return ''
  }
}

function rememberCert(path: string) {
  try {
    localStorage.setItem(CERT_KEY, path)
  } catch {
    /* storage unavailable: nothing to remember */
  }
}

export function SignPdf() {
  const pdf = usePdfDoc()
  useToolRequest('sign-pdf', (path) => void pdf.open(path))
  return (
    <section className="tool tool-wide">
      <header className="tool-header">
        <h1>Sign PDF</h1>
        <p>Place a handwritten signature on the page, or sign digitally with a certificate so any later change to the file can be detected.</p>
      </header>
      <DocGate>{(doc) => <SignBody key={`${doc.path}|${doc.mtime}`} doc={doc} />}</DocGate>
    </section>
  )
}

function SignBody({ doc }: { doc: PdfInfo }) {
  const [mode, setMode] = useState<'electronic' | 'digital'>('electronic')
  return (
    <>
      <Signatures path={doc.path} />
      <div className="segmented" role="radiogroup">
        {(
          [
            ['electronic', 'Electronic signature'],
            ['digital', 'Digital signature (certificate)'],
          ] as const
        ).map(([id, label]) => (
          <button key={id} type="button" role="radio" aria-checked={mode === id} className={cls('segment', mode === id && 'is-on')} onClick={() => setMode(id)}>
            {label}
          </button>
        ))}
      </div>
      {mode === 'electronic' ? <Electronic doc={doc} /> : <Digital doc={doc} />}
    </>
  )
}

/** Existing digital signatures and whether they still hold. */
function Signatures({ path }: { path: string }) {
  const [list, setList] = useState<SignatureStatus[] | null>(null)
  const [error, setError] = useState<Error | null>(null)
  useEffect(() => {
    call('pdf_verify_signatures', path).then(setList, (err) => setError(toError(err)))
  }, [path])
  if (error) return <ErrorNotice error={error} />
  if (!list?.length) return null
  return (
    <div className="card sig-list">
      <h2 className="panel-title">Digital signatures in this file</h2>
      {list.map((s) => {
        const ok = s.intact && s.valid
        return (
          <div key={s.field} className={cls('sig-row', ok ? 'is-ok' : 'is-bad')}>
            <span className="health-icon">{ok ? '✓' : '!'}</span>
            <div>
              <strong title={s.signer_details ?? undefined}>{s.signer ?? s.field}</strong>
              <span className="muted small">
                {s.signed_at ? ` · signed ${new Date(s.signed_at).toLocaleString()}` : ''}
                {s.reason ? ` · ${s.reason}` : ''}
              </span>
              <p className="small">
                {s.error
                  ? s.error
                  : !s.intact
                    ? 'The document was changed after it was signed — this signature no longer matches.'
                    : !s.valid
                      ? 'The signature is not valid.'
                      : s.covers_whole_file
                        ? 'Intact: the document has not changed since it was signed.'
                        : 'Intact, but content was added after signing (for example another signature).'}
                {ok && !s.trusted && ' The certificate is self-signed or not from an authority Windows trusts.'}
              </p>
            </div>
          </div>
        )
      })}
    </div>
  )
}

function Electronic({ doc }: { doc: PdfInfo }) {
  const pdf = usePdfDoc()
  const flow = useSaveFlow()
  const [sig, setSig] = useState<Signature | null>(null)
  const [objects, setObjects] = useState<EditObj[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [current, setCurrent] = useState(0)
  const page = doc.pages[current]

  const remove = useCallback((id: string) => {
    setObjects((l) => l.filter((o) => o.id !== id))
    setSelected(null)
  }, [])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement
      if (selected && (e.key === 'Delete' || e.key === 'Backspace') && !['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)) remove(selected)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [selected, remove])

  function place(r: Rect) {
    if (!sig) return
    const w = r.w > 8 ? r.w : Math.min(170, page.width * 0.35)
    const h = r.w > 8 ? r.h : w / sig.ratio
    const x = r.w > 8 ? r.x : Math.max(0, Math.min(page.width - w, r.x - w / 2))
    const y = r.w > 8 ? r.y : Math.max(0, Math.min(page.height - h, r.y - h / 2))
    const o: EditObj = { id: newId(), type: 'image', page: current, x, y, w, h, src: sig.src, preview: sig.preview }
    setObjects((l) => [...l, o])
    setSelected(o.id)
  }

  function addText(text: string) {
    const o: EditObj = { id: newId(), type: 'text', page: current, x: page.width * 0.6, y: page.height * 0.85, w: 140, h: 16, text, size: 11, family: 'sans', color: '#111111' }
    setObjects((l) => [...l, o])
    setSelected(o.id)
  }

  const boxes = objects.filter((o) => o.page === current)

  return (
    <div className="split-layout">
      <div className="split-main">
        <PagePreview
          file={doc}
          index={current}
          page={page}
          maxHeight={720}
          overlay={(scale) => (
            <BoxLayer
              page={page}
              scale={scale}
              boxes={boxes.map((o) => ({ ...o, content: objectContent(o, scale), className: 'lbox-object' }))}
              selected={selected}
              onSelect={setSelected}
              onChange={(id, r) => setObjects((l) => l.map((o) => (o.id === id ? { ...o, ...r } : o)))}
              onCreate={sig ? place : undefined}
            />
          )}
        />
        <PageNav index={current} count={doc.page_count} onChange={setCurrent} />
      </div>
      <aside className="side-panel">
        {sig ? (
          <>
            <h2 className="panel-title">Your signature</h2>
            <div className="sig-preview">
              <img src={sig.preview} alt="Signature" />
            </div>
            <p className="muted small">Click on the page to place it (or drag to size it). Place it as often as you need; drag to move, Delete to remove.</p>
            <div className="button-row">
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => setSig(null)}>
                New signature
              </button>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => addText(new Date().toLocaleDateString())}>
                Add date
              </button>
              {selected && (
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => remove(selected)}>
                  Remove selected
                </button>
              )}
            </div>
            {selected && objects.find((o) => o.id === selected)?.type === 'text' && (
              <input
                className="text-input"
                value={objects.find((o) => o.id === selected)?.text ?? ''}
                onChange={(e) => setObjects((l) => l.map((o) => (o.id === selected ? { ...o, text: e.target.value } : o)))}
                aria-label="Text"
              />
            )}
          </>
        ) : (
          <SignaturePad onDone={setSig} />
        )}
        <p className="small">
          {objects.length} placed{objects.length ? ` on page${new Set(objects.map((o) => o.page)).size === 1 ? '' : 's'} ${[...new Set(objects.map((o) => o.page + 1))].sort((a, b) => a - b).join(', ')}` : ''}
        </p>
        <button
          type="button"
          className="btn btn-primary"
          disabled={flow.busy || !objects.length}
          onClick={() => flow.saveAs(doc.path, 'signed', (out) => call('pdf_apply_edits', doc.path, out, toPayload(objects)))}
        >
          {flow.busy ? 'Saving…' : 'Save signed PDF…'}
        </button>
        <ErrorNotice error={flow.error} />
        {flow.saved && <ResultCard files={flow.saved} onDismiss={flow.dismiss} onContinue={(f) => void pdf.open(f.path)} />}
      </aside>
    </div>
  )
}

function Digital({ doc }: { doc: PdfInfo }) {
  const pdf = usePdfDoc()
  const flow = useSaveFlow()
  const [cert, setCert] = useState(rememberedCert)
  const [password, setPassword] = useState('')
  const [info, setInfo] = useState<CertInfo | null>(null)
  const [certError, setCertError] = useState<Error | null>(null)
  const [creating, setCreating] = useState(false)
  const [reason, setReason] = useState('I approve this document')
  const [location, setLocation] = useState('')
  const [contact, setContact] = useState('')
  const [visible, setVisible] = useState(true)
  const [box, setBox] = useState<(Rect & { page: number }) | null>(null)
  const [current, setCurrent] = useState(doc.page_count - 1)
  const page = doc.pages[current]

  async function check(path = cert, pw = password) {
    setInfo(null)
    setCertError(null)
    try {
      setInfo(await call('cert_info', path, pw))
      rememberCert(path)
    } catch (err) {
      setCertError(toError(err))
    }
  }

  async function choose() {
    try {
      const [path] = await call('pick_files', 'Certificates', ['pfx', 'p12'], false)
      if (path) {
        setCert(path)
        setInfo(null)
      }
    } catch (err) {
      setCertError(toError(err))
    }
  }

  const stamp = visible ? (box ?? { page: current, x: page.width - 230, y: page.height - 100, w: 200, h: 64 }) : null

  return (
    <div className="split-layout">
      <div className="split-main">
        <PagePreview
          file={doc}
          index={current}
          page={page}
          maxHeight={720}
          overlay={(scale) =>
            stamp && stamp.page === current ? (
              <BoxLayer
                page={page}
                scale={scale}
                boxes={[{ id: 'stamp', ...stamp, className: 'lbox-stamp', content: <span className="lbox-label">Digitally signed by {info?.subject.split(',')[0] ?? '…'}</span> }]}
                selected="stamp"
                onSelect={() => undefined}
                onChange={(_, r) => setBox({ ...r, page: current })}
                onCreate={(r) => setBox({ page: current, x: r.x, y: r.y, w: r.w > 20 ? r.w : 200, h: r.w > 20 ? r.h : 64 })}
              />
            ) : stamp ? (
              <BoxLayer page={page} scale={scale} boxes={[]} selected={null} onSelect={() => undefined} onCreate={(r) => setBox({ page: current, x: r.x, y: r.y, w: r.w > 20 ? r.w : 200, h: r.w > 20 ? r.h : 64 })} />
            ) : null
          }
        />
        <PageNav index={current} count={doc.page_count} onChange={setCurrent} />
      </div>
      <aside className="side-panel">
        <h2 className="panel-title">Certificate</h2>
        {creating ? (
          <CreateCertificate
            onCancel={() => setCreating(false)}
            onCreated={(path, pw) => {
              setCreating(false)
              setCert(path)
              setPassword(pw)
              void check(path, pw)
            }}
          />
        ) : (
          <>
            <div className="button-row">
              <button type="button" className="btn btn-secondary btn-sm" onClick={choose}>
                {cert ? 'Change…' : 'Choose .pfx / .p12…'}
              </button>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => setCreating(true)}>
                Create a certificate…
              </button>
            </div>
            {cert && <p className="small mono break">{cert}</p>}
            {cert && (
              <label className="form-field">
                <span className="form-field-name">Certificate password</span>
                <div className="button-row">
                  <input
                    className="text-input"
                    type="password"
                    autoComplete="off"
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value)
                      setInfo(null)
                    }}
                    onKeyDown={(e) => e.key === 'Enter' && void check()}
                  />
                  <button type="button" className="btn btn-ghost btn-sm" onClick={() => void check()}>
                    Check
                  </button>
                </div>
              </label>
            )}
            <ErrorNotice error={certError} />
            {info && (
              <div className={cls('cert-info small', info.expired && 'is-bad')}>
                <strong>{info.subject}</strong>
                <span className="muted">
                  {info.self_signed ? 'Self-signed' : `Issued by ${info.issuer}`} · valid until {new Date(info.valid_until).toLocaleDateString()}
                  {info.expired && ' (expired)'}
                </span>
              </div>
            )}
          </>
        )}
        <h2 className="panel-title">Details</h2>
        <label className="form-field">
          <span className="form-field-name">Reason</span>
          <input className="text-input" value={reason} onChange={(e) => setReason(e.target.value)} />
        </label>
        <div className="field-grid">
          <label>
            Location
            <input className="text-input" value={location} onChange={(e) => setLocation(e.target.value)} />
          </label>
          <label>
            Contact
            <input className="text-input" value={contact} onChange={(e) => setContact(e.target.value)} />
          </label>
        </div>
        <label className="check">
          <input type="checkbox" checked={visible} onChange={(e) => setVisible(e.target.checked)} /> Show a signature box on the page
        </label>
        {visible && <p className="muted small">Click on a page to put the box there; drag its edges to resize.</p>}
        <button
          type="button"
          className="btn btn-primary"
          disabled={flow.busy || !info || info.expired}
          onClick={() =>
            flow.saveAs(doc.path, 'signed', (out) => call('pdf_sign', doc.path, out, cert, password, reason, location, contact, stamp))
          }
        >
          {flow.busy ? 'Signing…' : 'Sign and save…'}
        </button>
        {!info && cert && <p className="muted small">Enter the password and press Check to unlock the certificate.</p>}
        <ErrorNotice error={flow.error} />
        {flow.saved && <ResultCard files={flow.saved} onDismiss={flow.dismiss} onContinue={(f) => void pdf.open(f.path)} />}
      </aside>
    </div>
  )
}

function CreateCertificate({ onCreated, onCancel }: { onCreated: (path: string, password: string) => void; onCancel: () => void }) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [org, setOrg] = useState('')
  const [country, setCountry] = useState('')
  const [pw, setPw] = useState('')
  const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const mismatch = confirm !== '' && pw !== confirm
  const ok = name.trim() && pw.length >= 6 && pw === confirm && (!country || /^[A-Za-z]{2}$/.test(country))

  async function create() {
    setBusy(true)
    setError(null)
    try {
      const suggested = await call('cert_suggest_path', name)
      const out = await call('save_file_dialog', suggested, 'Certificate', ['pfx'])
      if (!out) return
      const res = await call('cert_create', out, pw, name.trim(), email.trim(), org.trim(), country.trim().toUpperCase())
      onCreated(res.path, pw)
    } catch (err) {
      setError(toError(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="card cert-create">
      <p className="muted small">Creates a self-signed certificate. Signatures made with it prove the file hasn’t changed, but readers will show the signer as not verified by an authority.</p>
      <label className="form-field">
        <span className="form-field-name">Your name</span>
        <input className="text-input" value={name} onChange={(e) => setName(e.target.value)} />
      </label>
      <div className="field-grid">
        <label>
          Email
          <input className="text-input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label>
          Organisation
          <input className="text-input" value={org} onChange={(e) => setOrg(e.target.value)} />
        </label>
        <label>
          Country (2 letters)
          <input className="text-input" value={country} maxLength={2} onChange={(e) => setCountry(e.target.value)} />
        </label>
      </div>
      <div className="field-grid">
        <label>
          Password (6+ characters)
          <input className="text-input" type="password" autoComplete="new-password" value={pw} onChange={(e) => setPw(e.target.value)} />
        </label>
        <label>
          Confirm
          <input className="text-input" type="password" autoComplete="new-password" aria-invalid={mismatch} value={confirm} onChange={(e) => setConfirm(e.target.value)} />
        </label>
      </div>
      {mismatch && <span className="field-error small">The passwords don’t match</span>}
      <ErrorNotice error={error} />
      <div className="button-row">
        <button type="button" className="btn btn-ghost btn-sm" onClick={onCancel}>
          Cancel
        </button>
        <button type="button" className="btn btn-primary btn-sm" disabled={!ok || busy} onClick={create}>
          {busy ? 'Creating…' : 'Create and save…'}
        </button>
      </div>
    </div>
  )
}
