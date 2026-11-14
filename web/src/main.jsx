import { useCallback, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import {
  ACTIVITY_KINDS,
  ApiError,
  STAGES,
  TASK_STATUSES,
  api,
  fmtDate,
  fmtDateTime,
} from './api.js'
import './style.css'

function Landing() {
  return (
    <div className="landing">
      <nav className="topnav" aria-label="Main">
        <a className="brandmark" href="/"><span className="dot" />Agentic OS</a>
        <div className="links">
          <a href="#how">How it works</a>
          <a href="#features">Features</a>
          <a href="#faq">FAQ</a>
          <a className="button" href="/login">Sign in</a>
        </div>
      </nav>

      <header className="hero">
        <p className="eyebrow">Autonomous Agentic OS</p>
        <h1>Turn a CRM task into a working tool.</h1>
        <p className="sub">
          Describe a follow-up workflow in plain English. The system generates
          Python, tests it in an isolated sandbox, repairs failures, and runs it
          against your CRM data — with versioned rollback.
        </p>
        <div className="ctas">
          <a className="button big" href="/login">Launch demo</a>
          <a className="button big secondary" href="#how">See how it works</a>
        </div>

        <div className="preview" aria-hidden="true">
          <div className="bar"><i /><i /><i /></div>
          <div className="mock">
            <div className="side">
              <i className="on" /><i /><i /><i /><i />
            </div>
            <div className="body">
              <div className="kpis">
                <div className="kpi"><b>30</b><span>Leads</span></div>
                <div className="kpi"><b>8</b><span>Companies</span></div>
                <div className="kpi"><b>13</b><span>Open tasks</span></div>
              </div>
              <table>
                <thead><tr><th>Lead</th><th>Stage</th><th>Last contact</th></tr></thead>
                <tbody>
                  <tr><td>Noah Weber</td><td><span className="badge gray">lost</span></td><td>Oct 18</td></tr>
                  <tr><td>Ava Okafor</td><td><span className="badge blue">contacted</span></td><td>Oct 13</td></tr>
                  <tr><td>Priya Nair</td><td><span className="badge green">qualified</span></td><td>Nov 10</td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </header>

      <section className="section" id="how">
        <h2>How it works</h2>
        <p className="lead">Three steps from a sentence to a running CRM tool.</p>
        <div className="steps">
          <div className="step">
            <div className="num">1</div>
            <h3>Describe</h3>
            <p>Write the workflow in plain English — e.g. “find leads idle for seven days and create a follow-up task”.</p>
          </div>
          <div className="step">
            <div className="num">2</div>
            <h3>Generate &amp; test</h3>
            <p>The system writes the tool, runs it in a locked-down container, and repairs failures — up to three attempts.</p>
          </div>
          <div className="step">
            <div className="num">3</div>
            <h3>Activate &amp; run</h3>
            <p>You review the tested version, activate it, and invoke it any time. Roll back to the previous version anytime.</p>
          </div>
        </div>
      </section>

      <section className="section" id="features">
        <h2>What&apos;s inside</h2>
        <p className="lead">A real CRM first — leads, companies, activities, and follow-up tasks — plus the AI tool pipeline.</p>
        <div className="features">
          <div className="feature">
            <div className="ico">L</div>
            <div>
              <h3>Lead follow-up engine</h3>
              <p>Find stale leads, draft follow-ups, and track every task back to its source lead.</p>
            </div>
          </div>
          <div className="feature">
            <div className="ico">Q</div>
            <div>
              <h3>Isolated QA</h3>
              <p>Generated code runs in a network-less Docker sandbox with no keys, no database, and hard limits.</p>
            </div>
          </div>
          <div className="feature">
            <div className="ico">V</div>
            <div>
              <h3>Versioned tools</h3>
              <p>Every passing version is immutable. Activate or roll back with one click — in-flight runs keep their version.</p>
            </div>
          </div>
          <div className="feature">
            <div className="ico">K</div>
            <div>
              <h3>Bring your own key</h3>
              <p>One sponsored AI task per account; afterwards use your own OpenRouter key, held in memory only.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="section faq" id="faq">
        <h2>Questions</h2>
        <details>
          <summary>Do I need my own API key?</summary>
          <p>Each invited account gets one sponsored AI generation task. After that, you can attach your own OpenRouter key for the session — it is never saved to the database or sent to generated-code containers.</p>
        </details>
        <details>
          <summary>Is this a finished product?</summary>
          <p>No — it&apos;s an internship prototype. It runs against sample CRM data in a single demo workspace. Public multi-tenant hardening is deliberately out of scope.</p>
        </details>
        <details>
          <summary>Where does my data live?</summary>
          <p>In a managed Postgres database (Neon). Generated tools receive a read-only snapshot and can only propose fixed CRM operations, which the server validates before writing.</p>
        </details>
      </section>

      <section className="cta-band">
        <div className="section">
          <h2>Ready to see it work?</h2>
          <p>Sign in with your invited account and generate your first tool.</p>
          <a className="button big" href="/login">Launch demo</a>
        </div>
      </section>

      <footer>Autonomous Agentic OS — internship prototype. Sample data only.</footer>
    </div>
  )
}

function Login({ onDone }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const result = await api('/auth/login', {
        method: 'POST',
        body: { email, password },
      })
      onDone(result.must_change_password)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Login failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="auth">
      <h1>Sign in</h1>
      <p className="muted">Invite-only demo workspace. Use the account credentials you were given.</p>
      <form onSubmit={submit} className="card">
        <label>
          Email
          <input
            type="email"
            required
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label>
          Password
          <input
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {error && <p role="alert" className="error">{error}</p>}
        <button className="button" disabled={busy}>
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
      <p><a href="/">Back to home</a></p>
    </main>
  )
}

function ChangePassword({ onDone }) {
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event) {
    event.preventDefault()
    if (next !== confirm) {
      setError('New passwords do not match')
      return
    }
    setBusy(true)
    setError('')
    try {
      await api('/auth/change-password', {
        method: 'POST',
        body: { current_password: current, new_password: next },
      })
      onDone()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not change password')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="auth">
      <h1>Set a new password</h1>
      <p>Your account requires a password change before continuing.</p>
      <form onSubmit={submit} className="card">
        <label>
          Current password
          <input type="password" required autoComplete="current-password"
            value={current} onChange={(e) => setCurrent(e.target.value)} />
        </label>
        <label>
          New password (min 10 characters)
          <input type="password" required minLength={10} autoComplete="new-password"
            value={next} onChange={(e) => setNext(e.target.value)} />
        </label>
        <label>
          Confirm new password
          <input type="password" required minLength={10} autoComplete="new-password"
            value={confirm} onChange={(e) => setConfirm(e.target.value)} />
        </label>
        {error && <p role="alert" className="error">{error}</p>}
        <button className="button" disabled={busy}>Save password</button>
      </form>
    </main>
  )
}

function ErrorNote({ error }) {
  if (!error) return null
  return <p role="alert" className="error">{error}</p>
}

const BADGE_TONES = {
  new: 'gray', contacted: 'blue', qualified: 'green', customer: 'green', lost: 'red',
  open: 'amber', done: 'green', cancelled: 'gray',
  passed: 'green', failed: 'red', active: 'green', draft: 'gray', retired: 'gray',
  awaiting_activation: 'amber', generating: 'blue', testing: 'blue', repairing: 'amber',
  queued: 'gray', needs_key: 'amber', succeeded: 'green',
}

function StatusBadge({ value }) {
  return <span className={`badge ${BADGE_TONES[value] || 'gray'}`}>{value}</span>
}

function LeadForm({ companies, onCreated }) {
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({
    name: '', email: '', company_id: '', stage: 'new',
    last_contact_date: '', value: '', currency: 'USD',
  })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  function set(key) {
    return (e) => setForm({ ...form, [key]: e.target.value })
  }

  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const body = {
        name: form.name,
        email: form.email,
        stage: form.stage,
        currency: form.currency || 'USD',
      }
      if (form.company_id) body.company_id = form.company_id
      if (form.last_contact_date) body.last_contact_date = form.last_contact_date
      if (form.value) body.value = form.value
      await api('/crm/leads', { method: 'POST', body })
      setForm({ name: '', email: '', company_id: '', stage: 'new', last_contact_date: '', value: '', currency: 'USD' })
      setOpen(false)
      onCreated()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not create lead')
    } finally {
      setBusy(false)
    }
  }

  if (!open) {
    return <button className="button" onClick={() => setOpen(true)}>New lead</button>
  }
  return (
    <form onSubmit={submit} className="card form-grid">
      <h2>New lead</h2>
      <label>Name <input required value={form.name} onChange={set('name')} /></label>
      <label>Email <input type="email" required value={form.email} onChange={set('email')} /></label>
      <label>Company
        <select value={form.company_id} onChange={set('company_id')}>
          <option value="">— none —</option>
          {companies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </label>
      <label>Stage
        <select value={form.stage} onChange={set('stage')}>
          {STAGES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </label>
      <label>Last contact <input type="date" value={form.last_contact_date} onChange={set('last_contact_date')} /></label>
      <label>Value <input type="number" min="0" step="0.01" value={form.value} onChange={set('value')} /></label>
      <label>Currency <input maxLength={3} value={form.currency} onChange={set('currency')} /></label>
      <ErrorNote error={error} />
      <div className="row">
        <button className="button" disabled={busy}>{busy ? 'Saving…' : 'Create'}</button>
        <button type="button" onClick={() => setOpen(false)}>Cancel</button>
      </div>
    </form>
  )
}

function LeadDetail({ leadId, companies, onChanged }) {
  const [lead, setLead] = useState(null)
  const [error, setError] = useState('')
  const [stage, setStage] = useState('')
  const [companyId, setCompanyId] = useState('')
  const [note, setNote] = useState({ kind: 'note', body: '' })
  const [task, setTask] = useState({ title: '', due_date: '' })
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    try {
      const data = await api(`/crm/leads/${leadId}`)
      setLead(data)
      setStage(data.stage)
      setCompanyId(data.company_id || '')
      setError('')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not load lead')
    }
  }, [leadId])

  useEffect(() => { load() }, [load])

  async function saveField(field, value) {
    setBusy(true)
    try {
      const body = { version: lead.version, [field]: value || null }
      await api(`/crm/leads/${leadId}`, { method: 'PATCH', body })
      await load()
      onChanged()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Update failed')
    } finally {
      setBusy(false)
    }
  }

  async function addActivity(event) {
    event.preventDefault()
    setBusy(true)
    try {
      await api(`/crm/leads/${leadId}/activities`, {
        method: 'POST',
        body: { kind: note.kind, body: note.body },
      })
      setNote({ kind: 'note', body: '' })
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not add activity')
    } finally {
      setBusy(false)
    }
  }

  async function addTask(event) {
    event.preventDefault()
    setBusy(true)
    try {
      await api('/crm/tasks', {
        method: 'POST',
        body: { title: task.title, due_date: task.due_date, lead_id: leadId },
      })
      setTask({ title: '', due_date: '' })
      await load()
      onChanged()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not add task')
    } finally {
      setBusy(false)
    }
  }

  async function toggleTask(t) {
    try {
      await api(`/crm/tasks/${t.id}`, {
        method: 'PATCH',
        body: { version: t.version, status: t.status === 'done' ? 'open' : 'done' },
      })
      await load()
      onChanged()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not update task')
    }
  }

  if (error && !lead) return <ErrorNote error={error} />
  if (!lead) return <p>Loading…</p>

  return (
    <section className="card">
      <h2>{lead.name}</h2>
      <ErrorNote error={error} />
      <dl className="details">
        <dt>Email</dt><dd>{lead.email}</dd>
        <dt>Stage</dt>
        <dd>
          <select value={stage} disabled={busy}
            onChange={(e) => { setStage(e.target.value); saveField('stage', e.target.value) }}>
            {STAGES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </dd>
        <dt>Company</dt>
        <dd>
          <select value={companyId} disabled={busy}
            onChange={(e) => { setCompanyId(e.target.value); saveField('company_id', e.target.value) }}>
            <option value="">— none —</option>
            {companies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </dd>
        <dt>Last contact</dt><dd>{fmtDate(lead.last_contact_date)}</dd>
        <dt>Value</dt><dd>{lead.value ? `${lead.value} ${lead.currency}` : '—'}</dd>
        <dt>Version</dt><dd>{lead.version}</dd>
      </dl>

      <h3>Activities</h3>
      {lead.activities.length === 0 && <p className="muted">No activities yet.</p>}
      <ul className="plain">
        {lead.activities.map((a) => (
          <li key={a.id}>
            <strong>{a.kind}</strong> · {fmtDateTime(a.occurred_at)} — {a.body}
          </li>
        ))}
      </ul>
      <form onSubmit={addActivity} className="row-form">
        <select value={note.kind} onChange={(e) => setNote({ ...note, kind: e.target.value })}>
          {ACTIVITY_KINDS.map((k) => <option key={k} value={k}>{k}</option>)}
        </select>
        <input required placeholder="Add a note or activity" value={note.body}
          onChange={(e) => setNote({ ...note, body: e.target.value })} />
        <button disabled={busy}>Add</button>
      </form>

      <h3>Follow-up tasks</h3>
      {lead.tasks.length === 0 && <p className="muted">No tasks yet.</p>}
      <ul className="plain">
        {lead.tasks.map((t) => (
          <li key={t.id}>
            <label>
              <input type="checkbox" checked={t.status === 'done'} onChange={() => toggleTask(t)} />{' '}
              <span className={t.status === 'done' ? 'done' : ''}>{t.title}</span>
            </label>{' '}
            <span className="muted">due {fmtDate(t.due_date)} · {t.status}</span>
          </li>
        ))}
      </ul>
      <form onSubmit={addTask} className="row-form">
        <input required placeholder="New follow-up task" value={task.title}
          onChange={(e) => setTask({ ...task, title: e.target.value })} />
        <input required type="date" value={task.due_date}
          onChange={(e) => setTask({ ...task, due_date: e.target.value })} />
        <button disabled={busy}>Add task</button>
      </form>
    </section>
  )
}

function LeadsView({ companies, refreshKey, onChanged }) {
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [search, setSearch] = useState('')
  const [stage, setStage] = useState('')
  const [selected, setSelected] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const limit = 25

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
      if (search) params.set('search', search)
      if (stage) params.set('stage', stage)
      const data = await api(`/crm/leads?${params}`)
      setItems(data.items)
      setTotal(data.total)
      setError('')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not load leads')
    } finally {
      setLoading(false)
    }
  }, [offset, search, stage])

  useEffect(() => { load() }, [load, refreshKey])

  return (
    <div>
      <div className="toolbar">
        <input placeholder="Search leads…" value={search}
          onChange={(e) => { setSearch(e.target.value); setOffset(0) }} />
        <select value={stage} onChange={(e) => { setStage(e.target.value); setOffset(0) }}>
          <option value="">All stages</option>
          {STAGES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <LeadForm companies={companies} onCreated={() => { setOffset(0); load(); onChanged() }} />
      </div>
      <ErrorNote error={error} />
      {loading && <p>Loading…</p>}
      {!loading && items.length === 0 && <p className="muted">No leads found.</p>}
      {items.length > 0 && (
        <table>
          <thead>
            <tr><th>Name</th><th>Email</th><th>Company</th><th>Stage</th><th>Last contact</th><th>Value</th></tr>
          </thead>
          <tbody>
            {items.map((l) => (
              <tr key={l.id} className={selected === l.id ? 'selected' : ''}
                onClick={() => setSelected(l.id)}>
                <td>{l.name}</td>
                <td>{l.email}</td>
                <td>{l.company_name || '—'}</td>
                <td><StatusBadge value={l.stage} /></td>
                <td>{fmtDate(l.last_contact_date)}</td>
                <td>{l.value ? `${l.value} ${l.currency}` : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <div className="row pager">
        <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}>← Prev</button>
        <span className="muted">{offset + 1}–{Math.min(offset + limit, total)} of {total}</span>
        <button disabled={offset + limit >= total} onClick={() => setOffset(offset + limit)}>Next →</button>
      </div>
      {selected && (
        <LeadDetail leadId={selected} companies={companies}
          onChanged={() => { load(); onChanged() }} />
      )}
    </div>
  )
}

function CompanyForm({ onCreated }) {
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ name: '', website: '', industry: '' })
  const [error, setError] = useState('')

  async function submit(event) {
    event.preventDefault()
    try {
      await api('/crm/companies', {
        method: 'POST',
        body: {
          name: form.name,
          website: form.website || null,
          industry: form.industry || null,
        },
      })
      setForm({ name: '', website: '', industry: '' })
      setOpen(false)
      onCreated()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not create company')
    }
  }

  if (!open) return <button className="button" onClick={() => setOpen(true)}>New company</button>
  return (
    <form onSubmit={submit} className="card form-grid">
      <h2>New company</h2>
      <label>Name <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
      <label>Website <input value={form.website} onChange={(e) => setForm({ ...form, website: e.target.value })} /></label>
      <label>Industry <input value={form.industry} onChange={(e) => setForm({ ...form, industry: e.target.value })} /></label>
      <ErrorNote error={error} />
      <div className="row">
        <button className="button">Create</button>
        <button type="button" onClick={() => setOpen(false)}>Cancel</button>
      </div>
    </form>
  )
}

function CompaniesView({ refreshKey }) {
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      const params = new URLSearchParams({ limit: '100' })
      if (search) params.set('search', search)
      const data = await api(`/crm/companies?${params}`)
      setItems(data.items)
      setTotal(data.total)
      setError('')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not load companies')
    }
  }, [search])

  useEffect(() => { load() }, [load, refreshKey])

  return (
    <div>
      <div className="toolbar">
        <input placeholder="Search companies…" value={search} onChange={(e) => setSearch(e.target.value)} />
        <CompanyForm onCreated={load} />
      </div>
      <ErrorNote error={error} />
      {items.length === 0 && <p className="muted">No companies found.</p>}
      {items.length > 0 && (
        <table>
          <thead><tr><th>Name</th><th>Industry</th><th>Website</th></tr></thead>
          <tbody>
            {items.map((c) => (
              <tr key={c.id}>
                <td>{c.name}</td>
                <td>{c.industry || '—'}</td>
                <td>{c.website || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="muted">{total} companies</p>
    </div>
  )
}

function TaskForm({ leads, onCreated }) {
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ title: '', due_date: '', lead_id: '' })
  const [error, setError] = useState('')

  async function submit(event) {
    event.preventDefault()
    try {
      const body = { title: form.title, due_date: form.due_date, status: 'open' }
      if (form.lead_id) body.lead_id = form.lead_id
      await api('/crm/tasks', { method: 'POST', body })
      setForm({ title: '', due_date: '', lead_id: '' })
      setOpen(false)
      onCreated()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not create task')
    }
  }

  if (!open) return <button className="button" onClick={() => setOpen(true)}>New task</button>
  return (
    <form onSubmit={submit} className="card form-grid">
      <h2>New follow-up task</h2>
      <label>Title <input required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></label>
      <label>Due date <input required type="date" value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} /></label>
      <label>Lead
        <select value={form.lead_id} onChange={(e) => setForm({ ...form, lead_id: e.target.value })}>
          <option value="">— none —</option>
          {leads.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
        </select>
      </label>
      <ErrorNote error={error} />
      <div className="row">
        <button className="button">Create</button>
        <button type="button" onClick={() => setOpen(false)}>Cancel</button>
      </div>
    </form>
  )
}

function TasksView({ refreshKey, leads }) {
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      const params = new URLSearchParams({ limit: '100' })
      if (status) params.set('status', status)
      const data = await api(`/crm/tasks?${params}`)
      setItems(data.items)
      setTotal(data.total)
      setError('')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not load tasks')
    }
  }, [status])

  useEffect(() => { load() }, [load, refreshKey])

  async function setTaskStatus(t, next) {
    try {
      await api(`/crm/tasks/${t.id}`, { method: 'PATCH', body: { version: t.version, status: next } })
      load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Update failed')
    }
  }

  const leadName = (id) => leads.find((l) => l.id === id)?.name || '—'

  return (
    <div>
      <div className="toolbar">
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          {TASK_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <TaskForm leads={leads} onCreated={load} />
      </div>
      <ErrorNote error={error} />
      {items.length === 0 && <p className="muted">No tasks found.</p>}
      {items.length > 0 && (
        <table>
          <thead><tr><th>Title</th><th>Lead</th><th>Due</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {items.map((t) => (
              <tr key={t.id}>
                <td className={t.status === 'done' ? 'done' : ''}>{t.title}</td>
                <td>{t.lead_id ? leadName(t.lead_id) : '—'}</td>
                <td>{fmtDate(t.due_date)}</td>
                <td><StatusBadge value={t.status} /></td>
                <td>
                  {t.status !== 'done' && (
                    <button onClick={() => setTaskStatus(t, 'done')}>Mark done</button>
                  )}
                  {t.status === 'done' && (
                    <button onClick={() => setTaskStatus(t, 'open')}>Reopen</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="muted">{total} tasks</p>
    </div>
  )
}

function SearchView() {
  const [q, setQ] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  async function run(event) {
    event.preventDefault()
    try {
      setResult(await api(`/crm/search?q=${encodeURIComponent(q)}`))
      setError('')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Search failed')
    }
  }

  return (
    <div>
      <form onSubmit={run} className="toolbar">
        <input placeholder="Search leads and companies…" value={q}
          onChange={(e) => setQ(e.target.value)} />
        <button className="button">Search</button>
      </form>
      <ErrorNote error={error} />
      {result && (
        <div className="card">
          <h3>Leads ({result.leads.length})</h3>
          <ul className="plain">
            {result.leads.map((l) => <li key={l.id}>{l.name} — {l.email}</li>)}
          </ul>
          <h3>Companies ({result.companies.length})</h3>
          <ul className="plain">
            {result.companies.map((c) => <li key={c.id}>{c.name}{c.industry ? ` — ${c.industry}` : ''}</li>)}
          </ul>
        </div>
      )}
    </div>
  )
}

function ByokModal({ onClose, onDone }) {
  const [key, setKey] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [agreed, setAgreed] = useState(false)

  async function submit(event) {
    event.preventDefault()
    if (!agreed) { setError('Please confirm the session-key agreement'); return }
    setBusy(true)
    setError('')
    try {
      await api('/session/provider-key', { method: 'POST', body: { api_key: key } })
      setKey('')
      onDone()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not attach key')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="card modal">
        <h2>Your included AI task has been used</h2>
        <p>Please enter your own OpenRouter API key to continue.</p>
        <p className="muted">Your key is used only for this session and is not saved in our database.</p>
        <form onSubmit={submit} className="form-grid">
          <label>
            OpenRouter API key
            <input type="password" required autoComplete="off" value={key}
              onChange={(e) => setKey(e.target.value)} />
          </label>
          <label className="check">
            <input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} />{' '}
            I agree that my key will be used to send my requests to OpenRouter and its
            selected provider. This app keeps the key only in temporary memory while
            needed. It does not intentionally write my key to the database, logs,
            browser storage, or generated-code containers. Provider data policies
            still apply.
          </label>
          <ErrorNote error={error} />
          <div className="row">
            <button className="button" disabled={busy}>{busy ? 'Attaching…' : 'Continue'}</button>
            <button type="button" onClick={onClose}>Cancel</button>
          </div>
        </form>
      </div>
    </div>
  )
}

const ACTIVE_RUN_STATES = new Set(['queued', 'needs_key', 'generating', 'testing', 'repairing'])

function RunCreator({ onCreated, sponsoredUsed, runnerOnline }) {
  const [prompt, setPrompt] = useState('')
  const [mode, setMode] = useState('sponsored')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [showKey, setShowKey] = useState(false)

  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const result = await api('/runs', {
        method: 'POST',
        body: {
          prompt,
          credential_mode: mode,
          idempotency_key: crypto.randomUUID(),
        },
      })
      setPrompt('')
      onCreated(result.run_id)
    } catch (err) {
      if (err instanceof ApiError && (err.status === 402 || err.status === 409)) {
        setShowKey(true)
      } else {
        setError(err instanceof ApiError ? err.message : 'Could not start run')
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="card">
      <h2>Describe a CRM tool</h2>
      <form onSubmit={submit} className="form-grid">
        <label>
          What should the tool do?
          <textarea required rows={3} value={prompt} onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g. Find leads with no activity for seven days and create a follow-up task" />
        </label>
        <label>
          AI credits
          <select value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="sponsored" disabled={sponsoredUsed}>
              Sponsored task{ sponsoredUsed ? ' (used)' : '' }
            </option>
            <option value="byok">My OpenRouter key (this session)</option>
          </select>
        </label>
        {!runnerOnline && <p className="error">Runner is offline — start the laptop worker to generate tools.</p>}
        <ErrorNote error={error} />
        <div className="row">
          <button className="button" disabled={busy || !runnerOnline}>
            {busy ? 'Starting…' : 'Generate tool'}
          </button>
        </div>
      </form>
      {showKey && (
        <ByokModal
          onClose={() => setShowKey(false)}
          onDone={() => { setShowKey(false); setMode('byok'); submit({ preventDefault() {} }) }}
        />
      )}
    </section>
  )
}

function RunRow({ run, selected, onSelect }) {
  return (
    <tr className={selected ? 'selected' : ''} onClick={() => onSelect(run.id)}>
      <td>{run.kind === 'generate' ? 'Generate' : 'Invoke'}</td>
      <td className="muted">{(run.prompt || run.id).slice(0, 60)}</td>
      <td><StatusBadge value={run.status} /></td>
      <td>{run.attempt_count ?? 0}/3</td>
      <td className="muted">{fmtDateTime(run.created_at)}</td>
    </tr>
  )
}

function RunDetail({ runId, tools, onChanged }) {
  const [run, setRun] = useState(null)
  const [error, setError] = useState('')
  const [activating, setActivating] = useState(false)

  const load = useCallback(async () => {
    try {
      setRun(await api(`/runs/${runId}`))
      setError('')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not load run')
    }
  }, [runId])

  useEffect(() => {
    load()
    const timer = setInterval(() => {
      setRun((current) => {
        if (current && !ACTIVE_RUN_STATES.has(current.status)) return current
        load()
        return current
      })
    }, 2000)
    return () => clearInterval(timer)
  }, [load])

  if (error) return <ErrorNote error={error} />
  if (!run) return <p>Loading run…</p>

  const terminal = !ACTIVE_RUN_STATES.has(run.status)
  const toolName = run.tool_version_id
    ? (tools.versions || []).find((v) => v.id === run.tool_version_id)?.name
    : null
  const toolVersion = run.tool_version_id
    ? (tools.versions || []).find((v) => v.id === run.tool_version_id)?.version
    : null

  async function activate() {
    if (!toolName || toolVersion == null) return
    setActivating(true)
    try {
      await api(`/tools/${toolName}/activate`, {
        method: 'POST',
        body: { version: toolVersion },
      })
      onChanged()
      load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Activation failed')
    } finally {
      setActivating(false)
    }
  }

  async function cancel() {
    try {
      await api(`/runs/${runId}/cancel`, { method: 'POST' })
      load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Cancel failed')
    }
  }

  return (
    <section className="card">
      <h2>Run {run.id.slice(0, 8)} — {run.status}</h2>
      {run.prompt && <p>{run.prompt}</p>}
      <p className="muted">
        kind={run.kind} · mode={run.credential_mode} · attempts={run.attempt_count}/3
        {run.error_code ? ` · error=${run.error_code}` : ''}
      </p>
      {!terminal && (
        <div className="row">
          <button onClick={cancel}>Cancel run</button>
        </div>
      )}
      {run.status === 'awaiting_activation' && toolName && (
        <div className="row">
          <button className="button" onClick={activate} disabled={activating}>
            {activating ? 'Activating…' : `Activate ${toolName} v${toolVersion}`}
          </button>
          <span className="muted">QA passed — review the tool, then activate.</span>
        </div>
      )}
      {run.status === 'needs_key' && (
        <p className="error">This run needs a provider key. Attach one below, then start a new run.</p>
      )}
      {run.kind === 'tool_invoke' && run.bundle?.display && (
        <div>
          <h3>Result</h3>
          <pre className="json">{JSON.stringify(run.bundle.display, null, 2)}</pre>
          {run.bundle.operations_result && (
            <p className="muted">Applied {run.bundle.operations_result.count} operation(s)</p>
          )}
        </div>
      )}
      <h3>Timeline</h3>
      <ul className="plain timeline">
        {(run.events || []).map((e) => (
          <li key={e.seq}>
            <span className="muted">#{e.seq}</span> <strong>{e.kind}</strong>{' '}
            <span className="muted">{fmtDateTime(e.created_at)}</span>
            {e.payload && Object.keys(e.payload).length > 0 && (
              <pre className="json inline">{JSON.stringify(e.payload)}</pre>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}

function RunsPanel({ tools, refreshKey, onToolsChanged, selectedRunId, onSelectRun }) {
  const [runs, setRuns] = useState([])
  const [statusInfo, setStatusInfo] = useState(null)
  const [error, setError] = useState('')
  const [showKey, setShowKey] = useState(false)

  const load = useCallback(async () => {
    try {
      const data = await api('/runs?limit=20')
      setRuns(data.items)
      setError('')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not load runs')
    }
    try {
      setStatusInfo(await api('/status'))
    } catch {}
  }, [])

  useEffect(() => {
    load()
    const timer = setInterval(load, 3000)
    return () => clearInterval(timer)
  }, [load, refreshKey])

  return (
    <div>
      {statusInfo && (
        <p className={statusInfo.runner_online ? 'muted' : 'error'}>
          Runner: {statusInfo.runner_online ? 'online' : 'offline'}
          {' · '}Sponsored task: {statusInfo.sponsored_task_used ? 'used' : 'available'}
        </p>
      )}
      <RunCreator
        sponsoredUsed={statusInfo?.sponsored_task_used}
        runnerOnline={statusInfo?.runner_online}
        onCreated={(id) => { load(); onSelectRun(id) }}
      />
      {showKey && (
        <ByokModal onClose={() => setShowKey(false)} onDone={() => { setShowKey(false); load() }} />
      )}
      <button className="linklike" onClick={() => setShowKey(true)}>Attach OpenRouter key for this session</button>
      <ErrorNote error={error} />
      {runs.length > 0 && (
        <table>
          <thead><tr><th>Type</th><th>Prompt</th><th>Status</th><th>Attempts</th><th>Created</th></tr></thead>
          <tbody>
            {runs.map((r) => <RunRow key={r.id} run={r} selected={selectedRunId === r.id} onSelect={onSelectRun} />)}
          </tbody>
        </table>
      )}
      {runs.length === 0 && <p className="muted">No runs yet.</p>}
      {selectedRunId && (
        <RunDetail runId={selectedRunId} tools={tools} onChanged={() => { load(); onToolsChanged() }} />
      )}
    </div>
  )
}

function ToolInvokeForm({ name, onInvoked }) {
  const [open, setOpen] = useState(false)
  const [inputText, setInputText] = useState('{}')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event) {
    event.preventDefault()
    let input
    try {
      input = JSON.parse(inputText || '{}')
    } catch {
      setError('Input must be valid JSON')
      return
    }
    setBusy(true)
    setError('')
    try {
      const res = await api(`/tools/${name}/invoke`, {
        method: 'POST',
        body: { input, idempotency_key: crypto.randomUUID() },
      })
      setOpen(false)
      onInvoked(res.run_id)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Invoke failed')
    } finally {
      setBusy(false)
    }
  }

  if (!open) return <button onClick={() => setOpen(true)}>Run tool</button>
  return (
    <form onSubmit={submit} className="card form-grid">
      <h3>Run {name}</h3>
      <label>
        Input (JSON)
        <textarea rows={3} value={inputText} onChange={(e) => setInputText(e.target.value)} />
      </label>
      <ErrorNote error={error} />
      <div className="row">
        <button className="button" disabled={busy}>{busy ? 'Starting…' : 'Execute'}</button>
        <button type="button" onClick={() => setOpen(false)}>Cancel</button>
      </div>
    </form>
  )
}

function ToolsPanel({ onInvoked }) {
  const [data, setData] = useState({ tools: [], versions: [] })
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      setData(await api('/tools'))
      setError('')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not load tools')
    }
  }, [])

  useEffect(() => { load() }, [load])

  async function act(name, version) {
    try {
      await api(`/tools/${name}/activate`, { method: 'POST', body: { version } })
      load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Activation failed')
    }
  }

  async function rollback(name) {
    try {
      await api(`/tools/${name}/rollback`, { method: 'POST', body: {} })
      load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Rollback failed')
    }
  }

  const byName = {}
  for (const v of data.versions) (byName[v.name] ||= []).push(v)

  return (
    <div>
      <ErrorNote error={error} />
      {data.tools.length === 0 && <p className="muted">No tools yet. Generate one from the AI runs tab.</p>}
      {data.tools.map((t) => {
        const versions = byName[t.name] || []
        return (
          <section className="card" key={t.name}>
            <h2>{t.name}</h2>
            <p className="muted">
              Active: {t.active_version ? `v${t.active_version}` : 'none'}
              {t.active_status ? ` (${t.active_status})` : ''}
            </p>
            <table>
              <thead><tr><th>Version</th><th>Status</th><th>Hash</th><th>Created</th><th></th></tr></thead>
              <tbody>
                {versions.map((v) => (
                  <tr key={v.id}>
                    <td>v{v.version}</td>
                    <td><StatusBadge value={v.status} /></td>
                    <td className="muted">{(v.source_hash || '').slice(0, 12)}…</td>
                    <td className="muted">{fmtDateTime(v.created_at)}</td>
                    <td>
                      {v.status === 'passed' && t.active_version !== v.version && (
                        <button onClick={() => act(t.name, v.version)}>Activate</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="row">
              {t.active_version != null && <button onClick={() => rollback(t.name)}>Rollback to previous</button>}
              {t.active_version != null && <ToolInvokeForm name={t.name} onInvoked={onInvoked} />}
            </div>
          </section>
        )
      })}
    </div>
  )
}

function UsagePanel() {
  const [data, setData] = useState(null)
  useEffect(() => {
    api('/tools/usage/today').then(setData).catch(() => setData({ items: [] }))
  }, [])
  if (!data) return null
  return (
    <section className="card">
      <h2>Today&apos;s AI usage</h2>
      {data.items.length === 0 && <p className="muted">No model calls recorded today.</p>}
      {data.items.length > 0 && (
        <table>
          <thead><tr><th>Model</th><th>Payer</th><th>Calls</th><th>Input tok</th><th>Output tok</th><th>Cost</th></tr></thead>
          <tbody>
            {data.items.map((u, i) => (
              <tr key={i}>
                <td>{u.model_id}</td>
                <td>{u.payer}</td>
                <td>{u.calls}</td>
                <td>{u.input_tokens}</td>
                <td>{u.output_tokens}</td>
                <td>{u.cost_usd != null ? `$${Number(u.cost_usd).toFixed(4)}` : (u.all_cost_known ? '$0.00' : 'unknown')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}

function Workspace() {
  const [me, setMe] = useState(null)
  const [authState, setAuthState] = useState('loading') // loading | anon | needs_password | ready
  const [tab, setTab] = useState('leads')
  const [refreshKey, setRefreshKey] = useState(0)
  const [companies, setCompanies] = useState([])
  const [leads, setLeads] = useState([])
  const [toolsData, setToolsData] = useState({ tools: [], versions: [] })
  const [selectedRunId, setSelectedRunId] = useState(null)

  useEffect(() => {
    api('/me')
      .then((data) => {
        setMe(data)
        setAuthState(data.must_change_password ? 'needs_password' : 'ready')
      })
      .catch((err) => setAuthState(err instanceof ApiError && err.status === 401 ? 'anon' : 'anon'))
  }, [])

  useEffect(() => {
    if (authState !== 'ready') return
    api('/crm/companies?limit=100').then((d) => setCompanies(d.items)).catch(() => {})
    api('/crm/leads?limit=100').then((d) => setLeads(d.items)).catch(() => {})
    api('/tools').then(setToolsData).catch(() => {})
  }, [authState])

  async function logout() {
    try { await api('/auth/logout', { method: 'POST' }) } catch {}
    window.location.href = '/'
  }

  if (authState === 'loading') return <main className="auth"><p>Loading…</p></main>
  if (authState === 'anon') {
    return (
      <main className="auth">
        <h1>Prototype workspace</h1>
        <p>You need to sign in first.</p>
        <p><a className="button" href="/login">Sign in</a></p>
      </main>
    )
  }
  if (authState === 'needs_password') {
    return <ChangePassword onDone={() => window.location.reload()} />
  }

  const tabs = [
    ['leads', 'Leads'],
    ['companies', 'Companies'],
    ['tasks', 'Tasks'],
    ['runs', 'AI runs'],
    ['tools', 'Tools'],
    ['search', 'Search'],
  ]
  const tabLabel = tabs.find(([k]) => k === tab)?.[1] || 'Workspace'

  return (
    <div className="app">
      <aside className="sidenav">
        <a className="brandmark" href="/"><span className="dot" />Agentic OS</a>
        {tabs.map(([key, label]) => (
          <button key={key} className={tab === key ? 'active' : ''}
            onClick={() => setTab(key)}>{label}</button>
        ))}
        <div className="spacer" />
        <div className="who">
          <div>{me.email}</div>
          <div className="muted-nav">{me.workspace_slug} workspace</div>
          <button onClick={logout}>Sign out</button>
        </div>
      </aside>
      <div className="maincol">
        <div className="topbar">
          <span className="appname">CRM Workspace</span>
          <span className="me">{me.workspace_slug}</span>
        </div>
        <div className="content">
          <h1>{tabLabel}</h1>
          {tab === 'leads' && (
        <LeadsView companies={companies} refreshKey={refreshKey}
          onChanged={() => setRefreshKey((k) => k + 1)} />
      )}
      {tab === 'companies' && <CompaniesView refreshKey={refreshKey} />}
      {tab === 'tasks' && <TasksView refreshKey={refreshKey} leads={leads} />}
      {tab === 'runs' && (
        <RunsPanel
          tools={toolsData}
          refreshKey={refreshKey}
          onToolsChanged={() => api('/tools').then(setToolsData).catch(() => {})}
          selectedRunId={selectedRunId}
          onSelectRun={setSelectedRunId}
        />
      )}
      {tab === 'tools' && (
        <ToolsPanel onInvoked={(id) => { setSelectedRunId(id); setTab('runs') }} />
      )}
          {tab === 'search' && <SearchView />}
          {tab === 'runs' && <UsagePanel />}
        </div>
      </div>
    </div>
  )
}

function App() {
  const path = window.location.pathname
  if (path === '/workspace') return <Workspace />
  if (path === '/login') return <Login onDone={(needsPw) => { window.location.href = '/workspace' }} />
  return <Landing />
}

createRoot(document.getElementById('root')).render(<App />)
