import { useEffect, useRef, useState } from 'react'
import { buildEvents } from './Studio.jsx'
import { ArrowUpIcon, ArrowUpRightIcon, CalendarCheckIcon, ListChecksIcon, ReceiptIcon, SparkleIcon, SquaresFourIcon, TreeStructureIcon } from '@phosphor-icons/react'
import './zeta.css'

const starters = [
  ['Project tracker', 'Build a project tracker with name, owner, due date, and status: planned, in progress, or done.', ListChecksIcon],
  ['Team expenses', 'Build an expense tracker with expense, amount, category, date, and whether it has been reimbursed.', ReceiptIcon],
  ['Event planning', 'Build an event checklist with task, owner, deadline, priority, and a checkbox for done.', CalendarCheckIcon],
]
const labels = { inspect: 'Read request', generate: 'Generate app', validate: 'Validate schema', repair: 'Repair', ready: 'Preview ready', applied: 'Applied', error: 'Build stopped', discarded: 'Draft discarded' }

function AgentTrace({ steps, busy }) {
  const phases = []
  for (const step of steps) {
    if (step.kind === 'generate') phases.push({ step, children: [] })
    else if (['validate', 'repair'].includes(step.kind) && phases.at(-1)?.children) phases.at(-1).children.push(step)
    else phases.push({ step })
  }
  return (
    <details className="zeta-trace" open>
      <summary><TreeStructureIcon aria-hidden="true" /> Agent trace <small>{busy ? 'Running' : `${steps.length} events`}</small></summary>
      <ol>
        {phases.map(({ step, children }, index) => (
          <li key={index} className={`zeta-trace-${step.kind}`}>
            <strong>{labels[step.kind]}</strong><p>{step.message}</p>
            {!!children?.length && <ul>{children.map((child, i) => <li key={i}><strong>{labels[child.kind]}</strong><p>{child.message}</p></li>)}</ul>}
          </li>
        ))}
        {busy && <li className="zeta-working">Working…</li>}
      </ol>
    </details>
  )
}

function RecordInput({ field, value }) {
  if (field.type === 'select') {
    return <select name={field.key} defaultValue={value ?? ''}>
      <option value="">Choose {field.label.toLowerCase()}</option>
      {field.options.map((option) => <option key={option}>{option}</option>)}
    </select>
  }
  if (field.type === 'checkbox') return <input name={field.key} type="checkbox" defaultChecked={value === true} />
  const numeric = field.type === 'number' || field.type === 'currency'
  return <input name={field.key} type={numeric ? 'number' : field.type} step={numeric ? 'any' : undefined}
    maxLength={field.type === 'text' ? 300 : undefined} defaultValue={value ?? ''} />
}

function AppPreview({ app, rows, onRows, draft }) {
  const [editing, setEditing] = useState(null)
  const [showForm, setShowForm] = useState(false)

  function save(event) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const values = Object.fromEntries(app.fields.map(({ key, type }) => [
      key, type === 'checkbox' ? form.has(key) : String(form.get(key) ?? '').trim(),
    ]))
    if (Object.values(values).every((value) => value === '')) return
    onRows((current) => editing
      ? current.map((row) => row.id === editing.id ? { ...row, values: { ...row.values, ...values } } : row)
      : [...current, { id: crypto.randomUUID(), values }])
    setEditing(null)
    setShowForm(false)
  }

  return (
    <div className="zeta-app">
      <div className="zeta-app-title">
        <div><h2>{app.name}</h2><p>{app.description}</p></div>
        {!draft && !showForm && <button className="zeta-primary" type="button" onClick={() => { setEditing(null); setShowForm(true) }}>+ Add {app.entity.toLowerCase()}</button>}
      </div>
      {showForm && !draft && (
        <form className="zeta-record-form" key={editing?.id ?? 'new'} onSubmit={save}>
          {app.fields.map((field) => <label key={field.key}><span>{field.label}</span><RecordInput field={field} value={editing?.values[field.key]} /></label>)}
          <div><button className="zeta-primary">Save record</button> <button type="button" className="zeta-secondary" onClick={() => setShowForm(false)}>Cancel</button></div>
        </form>
      )}
      <div className="zeta-records">
        <table aria-label={`${app.entity} records`}>
          <thead><tr>{app.fields.map((field) => <th key={field.key} scope="col">{field.label}</th>)}{!draft && <th scope="col">Actions</th>}</tr></thead>
          <tbody>{rows.map((row) => <tr key={row.id}>
            {app.fields.map(({ key, type }) => <td key={key}>{type === 'checkbox' && typeof row.values[key] === 'boolean' ? (row.values[key] ? 'Yes' : 'No') : row.values[key] || '—'}</td>)}
            {!draft && <td className="zeta-actions">
              <button type="button" onClick={() => { setEditing(row); setShowForm(true) }}>Edit</button>
              <button type="button" onClick={() => { if (editing?.id === row.id) { setEditing(null); setShowForm(false) }; onRows((current) => current.filter((item) => item.id !== row.id)) }}>Delete</button>
            </td>}
          </tr>)}</tbody>
        </table>
        {!rows.length && <p>No records yet. {draft ? 'Apply the draft to start adding records.' : 'Add a record to get started.'}</p>}
      </div>
    </div>
  )
}

export function Zeta({ userId }) {
  const storageKey = `agentic-os:zeta:${userId}`
  const [project, setProject] = useState(() => {
    try { return JSON.parse(localStorage.getItem(storageKey)) || { app: null, rows: [] } } catch { return { app: null, rows: [] } }
  })
  const [draft, setDraft] = useState(null)
  const [prompt, setPrompt] = useState('')
  const [runs, setRuns] = useState([])
  const [ask, setAsk] = useState(true)
  const [busy, setBusy] = useState(false)
  const [showSpec, setShowSpec] = useState(false)
  const [storageError, setStorageError] = useState(false)
  const controller = useRef(null)
  const transcript = useRef(null)
  const input = useRef(null)
  const preview = draft?.app ?? project.app

  useEffect(() => () => controller.current?.abort(), [])
  useEffect(() => {
    try { localStorage.setItem(storageKey, JSON.stringify(project)); setStorageError(false) }
    catch { setStorageError(true) }
  }, [project, storageKey])
  useEffect(() => { if (transcript.current) transcript.current.scrollTop = transcript.current.scrollHeight }, [runs])

  function append(id, step) {
    setRuns((current) => current.map((run) => run.id === id ? { ...run, steps: [...run.steps, step] } : run))
  }

  function apply(id, app) {
    setProject((current) => ({ ...current, app }))
    setDraft(null)
    setShowSpec(false)
    append(id, { kind: 'applied', message: 'The new app is live in your workspace.' })
  }

  async function submit(event) {
    event.preventDefault()
    if (controller.current || draft || prompt.trim().length < 3) return
    const id = crypto.randomUUID()
    const request = prompt.trim()
    const abort = new AbortController()
    controller.current = abort
    setBusy(true)
    setPrompt('')
    setRuns((current) => [...current, { id, prompt: request, steps: [] }])
    try {
      let finished = false
      for await (const { kind, message, app } of buildEvents({ prompt: request, current: project.app }, abort.signal, '/zeta/build')) {
        append(id, { kind, message })
        if (kind === 'ready') {
          finished = true
          if (ask) { setDraft({ id, app }); setShowSpec(false) }
          else apply(id, app)
        } else if (kind === 'error') {
          finished = true
          setPrompt(request)
        }
      }
      if (!finished) throw new Error('The connection ended before Zeta finished building.')
    } catch (error) {
      if (!abort.signal.aborted) { append(id, { kind: 'error', message: error.message }); setPrompt(request) }
    } finally {
      controller.current = null
      if (!abort.signal.aborted) setBusy(false)
    }
  }

  return (
    <div className="zeta">
      <header className="zeta-heading">
        <span className="zeta-mark" aria-hidden="true"><SparkleIcon /></span>
        <div><h1>Zeta</h1><p>Application builder</p></div>
        {project.app && <span className="zeta-project">{project.app.name}</span>}
      </header>
      <div className="zeta-layout">
        <section className="zeta-chat" aria-label="Zeta assistant">
          <header className="zeta-panel-head"><h2>Assistant</h2><span>OpenRouter</span></header>
          <div className="zeta-transcript" ref={transcript} role="log" aria-label="Conversation">
            {!runs.length && (
              <div className="zeta-welcome">
                <span className="zeta-spark" aria-hidden="true"><SparkleIcon /></span>
                <h2>{project.app ? `What should change in ${project.app.name}?` : 'What would you like to build?'}</h2>
                <p>{project.app ? 'Describe the fields you want to add or refine.' : 'Describe an app for managing records, or start with an idea below.'}</p>
                {!project.app && <div className="zeta-starters">{starters.map(([label, example, Icon]) => (
                  <button key={label} type="button" onClick={() => { setPrompt(example); input.current?.focus() }}><Icon aria-hidden="true" />{label}<ArrowUpRightIcon aria-hidden="true" /></button>
                ))}</div>}
              </div>
            )}
            {runs.map((run) => <article key={run.id} className="zeta-turn"><p className="zeta-prompt">{run.prompt}</p><AgentTrace steps={run.steps} busy={busy && run.id === runs.at(-1)?.id} /></article>)}
          </div>
          {draft && <div className="zeta-review"><strong>Review your draft</strong><div>
            <button type="button" className="zeta-secondary" onClick={() => { append(draft.id, { kind: 'discarded', message: 'The workspace kept its active version.' }); setDraft(null); setShowSpec(false) }}>Discard</button>
            <button type="button" className="zeta-primary" onClick={() => apply(draft.id, draft.app)}>Apply app</button>
          </div></div>}
          <form className="zeta-compose" onSubmit={submit}>
            <textarea ref={input} aria-label="Ask Zeta" rows={3} maxLength={1600} placeholder={project.app ? 'Describe a change…' : 'Describe the app you want to build…'} value={prompt} onChange={(event) => setPrompt(event.target.value)} />
            <div className="zeta-compose-bar"><label><input type="checkbox" checked={ask} disabled={busy || !!draft} onChange={(event) => setAsk(event.target.checked)} /> Ask before applying</label>
              <button className="zeta-primary" disabled={busy || !!draft || prompt.trim().length < 3}>{busy ? 'Building…' : 'Build'} <ArrowUpIcon aria-hidden="true" /></button>
            </div>
          </form>
        </section>
        <section className="zeta-preview" aria-label="Application preview">
          <header className="zeta-panel-head"><h2>App preview</h2>{preview && <div className="zeta-view-toggle" role="group" aria-label="Preview mode">
            <button type="button" aria-pressed={!showSpec} onClick={() => setShowSpec(false)}>Preview</button>
            <button type="button" aria-pressed={showSpec} onClick={() => setShowSpec(true)}>App spec</button>
          </div>}</header>
          <div className="zeta-preview-body">
            {storageError && <p role="status" className="zeta-storage-error">Browser storage is full or unavailable. Changes will last for this session.</p>}
            {preview ? <>
              <div className="zeta-preview-status"><span />{draft ? 'Draft preview' : 'Active app'}</div>
              {showSpec ? <pre className="zeta-code">{JSON.stringify(preview, null, 2)}</pre> : <AppPreview key={draft ? 'draft' : 'active'} app={preview} rows={project.rows} draft={!!draft} onRows={(update) => setProject((current) => ({ ...current, rows: update(current.rows) }))} />}
            </> : <div className="zeta-preview-empty"><span aria-hidden="true"><SquaresFourIcon /></span><h3>Your app will appear here</h3><p>Send a prompt to get started.</p></div>}
          </div>
        </section>
      </div>
    </div>
  )
}
