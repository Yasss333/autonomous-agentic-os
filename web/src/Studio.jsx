import { useEffect, useRef, useState } from 'react'
import { apiFetch } from './api.js'
import samples from './studio-samples.json'
import { AddressBookIcon, ArrowUpIcon, ArrowUpRightIcon, PackageIcon, ReceiptIcon, SparkleIcon } from '@phosphor-icons/react'
import './studio.css'

const sampleIcons = { crm: AddressBookIcon, expenses: ReceiptIcon, inventory: PackageIcon }

const money = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 })
const number = new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 })
const compare = {
  eq: (a, b) => a === b,
  ne: (a, b) => a !== b,
  contains: (a, b) => a.includes(b),
  gt: (a, b) => a > b,
  gte: (a, b) => a >= b,
  lt: (a, b) => a < b,
  lte: (a, b) => a <= b,
}
const stepLabels = {
  inspect: 'Read sample', generate: 'Generate', validate: 'Validate',
  repair: 'Repair', ready: 'Preview ready', applied: 'Applied', error: 'Build stopped',
}

function format(value, field, sample) {
  if (sample.fields[field] === 'money') return money.format(value)
  return typeof value === 'number' ? number.format(value) : value
}

function Dashboard({ sample, view, version, preview }) {
  const rows = sample.rows.filter((row) => view.filters.every((filter) => {
    const left = row[filter.field]
    const right = filter.compare_field ? row[filter.compare_field] : filter.value
    return typeof left === 'string'
      ? compare[filter.op](left.toLowerCase(), right.toLowerCase())
      : compare[filter.op](left, right)
  }))
  if (view.sort) {
    const { field, direction } = view.sort
    rows.sort((a, b) => (typeof a[field] === 'string'
      ? a[field].localeCompare(b[field]) : a[field] - b[field]) * (direction === 'desc' ? -1 : 1))
  }
  const groups = new Map()
  if (view.chart) {
    for (const row of rows) {
      const group = row[view.chart.group]
      groups.set(group, (groups.get(group) ?? 0) + row[view.chart.field])
    }
  }
  const largest = Math.max(1, ...groups.values())

  return (
    <section className="studio-dashboard" aria-label={preview ? 'Proposed dashboard' : 'Active dashboard'}>
      <header className="studio-preview-header">
        <span><span className="studio-indicator" />{preview ? 'Draft preview' : 'Active dashboard'}</span>
        <span className="studio-version">v{version}</span>
      </header>
      <div className="studio-dashboard-content">
        <h2>{view.title}</h2>
        <p>{view.summary}</p>
        {view.metrics.length > 0 && (
          <div className="studio-metrics">
            {view.metrics.map((metric, index) => {
              const total = rows.reduce((sum, row) => sum + (row[metric.field] ?? 0), 0)
              const value = metric.operation === 'count' ? rows.length
                : metric.operation === 'average' ? total / Math.max(1, rows.length) : total
              return <div key={index}><span>{metric.label}</span><strong>{format(value, metric.field, sample)}</strong></div>
            })}
          </div>
        )}
        {view.chart && groups.size > 0 && (
          <section className="studio-chart" aria-label={view.chart.label}>
            <h3>{view.chart.label}</h3>
            {[...groups].map(([label, amount]) => (
              <div key={label} className="studio-chart-row">
                <span>{label}</span>
                <span className="studio-chart-track"><span style={{ width: `${Math.max(0, amount) / largest * 100}%` }} /></span>
                <strong>{format(amount, view.chart.field, sample)}</strong>
              </div>
            ))}
          </section>
        )}
        <section className="studio-records">
          <header><h3>{sample.entity}</h3><span>{rows.length} records</span></header>
          <div className="studio-table-scroll">
            <table aria-label={sample.entity}>
              <thead><tr>{view.columns.map((field) => <th key={field} scope="col">{sample.labels[field]}</th>)}</tr></thead>
              <tbody>{rows.map((row) => (
                <tr key={row[Object.keys(sample.fields)[0]]}>
                  {view.columns.map((field) => <td key={field}>{format(row[field], field, sample)}</td>)}
                </tr>
              ))}</tbody>
            </table>
          </div>
          {!rows.length && <p className="studio-empty-table">No records match this view.</p>}
        </section>
      </div>
    </section>
  )
}

export async function* buildEvents(payload, signal, endpoint = '/studio/build') {
  const response = await apiFetch(endpoint, {
    method: 'POST',
    body: payload,
    signal,
  })
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(typeof error.detail === 'string' ? error.detail : 'Unable to start the build.')
  }
  if (!response.body) throw new Error('The build did not return a trace.')
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
  let pending = ''
  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      const lines = (pending + value).split('\n')
      pending = lines.pop()
      for (const line of lines) if (line.trim()) yield JSON.parse(line)
    }
    if (pending.trim()) yield JSON.parse(pending)
  } finally {
    await reader.cancel().catch(() => {})
    reader.releaseLock()
  }
}

function SampleChat({ id, sample, userId }) {
  const Icon = sampleIcons[id]
  const storageKey = `agentic-os:studio:${userId}:${id}`
  const [versions, setVersions] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey))
      if (Array.isArray(saved) && saved.length) return saved
    } catch { /* Storage is optional for a local sample. */ }
    return [sample.initial]
  })
  const active = versions.at(-1)
  const [draft, setDraft] = useState(null)
  const [prompt, setPrompt] = useState('')
  const [ask, setAsk] = useState(true)
  const [showOriginal, setShowOriginal] = useState(false)
  const [runs, setRuns] = useState([])
  const [busy, setBusy] = useState(false)
  const activeFetch = useRef(null)
  const transcriptEnd = useRef(null)

  useEffect(() => () => activeFetch.current?.abort(), [])
  useEffect(() => {
    try { localStorage.setItem(storageKey, JSON.stringify(versions)) } catch { /* Browser storage may be disabled. */ }
  }, [storageKey, versions])
  useEffect(() => { transcriptEnd.current?.scrollIntoView({ block: 'nearest' }) }, [runs])

  function append(runId, step) {
    setRuns((current) => current.map((run) => run.id === runId
      ? { ...run, steps: [...run.steps, step] } : run))
  }

  function apply(runId, dashboard) {
    setShowOriginal(false)
    setVersions((current) => [...current, dashboard])
    setDraft(null)
    append(runId, { kind: 'applied', message: 'The new dashboard is active in this workspace.' })
  }

  async function submit(event) {
    event.preventDefault()
    const request = prompt.trim()
    if (request.length < 3 || activeFetch.current || draft) return
    const runId = crypto.randomUUID()
    const controller = new AbortController()
    activeFetch.current = controller
    setPrompt('')
    setBusy(true)
    setRuns((current) => [...current, { id: runId, prompt: request, steps: [] }])
    try {
      let terminal = false
      for await (const step of buildEvents({ sample: id, prompt: request, current: active }, controller.signal)) {
        append(runId, { kind: step.kind, message: step.message })
        if (step.kind === 'ready') {
          terminal = true
          setShowOriginal(false)
          if (ask) setDraft({ runId, dashboard: step.dashboard })
          else apply(runId, step.dashboard)
        }
        if (step.kind === 'error') terminal = true
      }
      if (!terminal) throw new Error('The connection ended before the build finished.')
    } catch (error) {
      if (controller.signal.aborted) return
      append(runId, { kind: 'error', message: error.message })
    } finally {
      activeFetch.current = null
      if (!controller.signal.aborted) setBusy(false)
    }
  }

  return (
    <div className={`studio-split studio-${sample.palette}`}>
      <section className="studio-chat" aria-label={`${sample.name} assistant`}>
        <header className="studio-chat-header"><span className="studio-appicon" aria-hidden="true"><Icon size="1.35rem" /></span><div><h2>{sample.name}</h2><p>Build with the assistant</p></div></header>
        <div className="studio-transcript" role="log" aria-label="Conversation and agent trace">
          {runs.length === 0 && (
            <div className="studio-chat-empty">
              <span className="studio-spark" aria-hidden="true"><SparkleIcon /></span>
              <h3>What would you like to change?</h3>
              <p>Ask for a view, filter, metric, or chart using this sample’s data.</p>
              <button type="button" className="studio-suggestion" onClick={() => setPrompt(sample.suggestion)}>{sample.suggestion} <ArrowUpRightIcon aria-hidden="true" /></button>
            </div>
          )}
          {runs.map((run) => (
            <div key={run.id} className="studio-turn">
              <p className="studio-message">{run.prompt}</p>
              <div className="studio-agent-label">Agent trace</div>
              <ol className="studio-trace">
                {run.steps.map((step, index) => (
                  <li key={index} className={`studio-step studio-step-${step.kind}`}><strong>{stepLabels[step.kind]}</strong><span>{step.message}</span></li>
                ))}
                {busy && run.id === runs.at(-1)?.id && <li className="studio-step studio-step-working"><span>Working…</span></li>}
              </ol>
            </div>
          ))}
          <div ref={transcriptEnd} />
        </div>
        {draft && (
          <div className="studio-review">
            <strong>Review the draft preview</strong>
            <div>
              <button type="button" className="studio-secondary" onClick={() => setDraft(null)}>Discard</button>
              <button type="button" className="studio-primary" onClick={() => apply(draft.runId, draft.dashboard)}>Apply changes</button>
            </div>
          </div>
        )}
        <form className="studio-compose" onSubmit={submit}>
          <textarea aria-label="Dashboard change request" placeholder="Ask for a change…" required maxLength={1600}
            rows={3} value={prompt} onChange={(event) => setPrompt(event.target.value)} />
          <div className="studio-compose-actions">
            <label className="studio-approval"><input type="checkbox" checked={ask} disabled={busy || !!draft} onChange={(event) => setAsk(event.target.checked)} /> Ask before applying</label>
            <button className="studio-primary" disabled={busy || !!draft || prompt.trim().length < 3}>Build <ArrowUpIcon aria-hidden="true" /></button>
          </div>
        </form>
      </section>
      <div className="studio-preview">
        <div className="studio-preview-controls" role="group" aria-label="Dashboard view">
          <button type="button" className="studio-secondary" aria-pressed={!showOriginal} onClick={() => setShowOriginal(false)}>Editable preview</button>
          <button type="button" className="studio-secondary" aria-pressed={showOriginal} onClick={() => setShowOriginal(true)}>Original dashboard</button>
        </div>
        {showOriginal ? (
          <div className="studio-dashboard studio-original">
            {id === 'expenses' ? <p>Chronicle opens on its original site.</p> : (
              <iframe title={sample.referenceLabel} src={sample.reference} sandbox="allow-scripts allow-same-origin" referrerPolicy="no-referrer" />
            )}
            <a className="studio-reference" href={sample.reference} target="_blank" rel="noreferrer">Open {sample.referenceLabel} in a new tab <ArrowUpRightIcon aria-hidden="true" /></a>
          </div>
        ) : <Dashboard sample={sample} view={draft?.dashboard ?? active} version={versions.length + Number(!!draft)} preview={!!draft} />}
        {versions.length > 1 && !showOriginal && !draft && !busy && (
          <button type="button" className="studio-secondary studio-rollback" onClick={() => setVersions((current) => current.slice(0, -1))}>
            Roll back to v{versions.length - 1}
          </button>
        )}
      </div>
    </div>
  )
}

export function Studio({ userId }) {
  const [selected, setSelected] = useState(null)
  const [opened, setOpened] = useState([])
  function open(id) {
    setSelected(id)
    setOpened((current) => current.includes(id) ? current : [...current, id])
  }
  return (
    <div className="studio">
      <nav aria-label="Sample apps" className={selected ? 'studio-sample-nav' : 'studio-sample-grid'}>
        {Object.entries(samples).map(([id, sample]) => {
          const Icon = sampleIcons[id]
          return (
            <button type="button" key={id} className={`studio-sample studio-${sample.palette}`} aria-pressed={selected === id} onClick={() => open(id)}>
              <span className="studio-appicon" aria-hidden="true"><Icon size="1.35rem" /></span>
              <span><strong>{sample.name}</strong>{!selected && <small>{sample.description}</small>}</span>
              <ArrowUpRightIcon aria-hidden="true" className="studio-whitespace" size="1.15em" />
            </button>
          )
        })}
      </nav>
      {opened.map((id) => (
        <div key={id} hidden={selected !== id}><SampleChat id={id} sample={samples[id]} userId={userId} /></div>
      ))}
      {!selected && <p className="studio-start">Open a sample to see its dashboard and ask the assistant to change it.</p>}
    </div>
  )
}
