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
    <main>
      <p className="eyebrow">Autonomous Agentic OS</p>
      <h1>Turn a CRM task into a working tool.</h1>
      <p>
        Describe a follow-up workflow in plain English. The prototype generates,
        tests, and runs CRM tools against sample data.
      </p>
      <p>
        <a className="button" href="/workspace">Open prototype workspace</a>{' '}
        <a href="/login">Sign in</a>
      </p>
    </main>
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
    <main>
      <h1>Sign in</h1>
      <p>Invite-only demo workspace. Use the account credentials you were given.</p>
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
    <main>
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
                <td>{l.stage}</td>
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
                <td>{t.status}</td>
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

function Workspace() {
  const [me, setMe] = useState(null)
  const [authState, setAuthState] = useState('loading') // loading | anon | needs_password | ready
  const [tab, setTab] = useState('leads')
  const [refreshKey, setRefreshKey] = useState(0)
  const [companies, setCompanies] = useState([])
  const [leads, setLeads] = useState([])

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
  }, [authState])

  async function logout() {
    try { await api('/auth/logout', { method: 'POST' }) } catch {}
    window.location.href = '/'
  }

  if (authState === 'loading') return <main><p>Loading…</p></main>
  if (authState === 'anon') {
    return (
      <main>
        <h1>Prototype workspace</h1>
        <p>You need to sign in first.</p>
        <p><a className="button" href="/login">Sign in</a></p>
      </main>
    )
  }
  if (authState === 'needs_password') {
    return <ChangePassword onDone={() => window.location.reload()} />
  }

  return (
    <main className="workspace">
      <header className="workspace-header">
        <div>
          <p className="eyebrow">Autonomous Agentic OS</p>
          <h1>Workspace</h1>
        </div>
        <div className="row">
          <span className="muted">{me.email} · {me.workspace_slug}</span>
          <button onClick={logout}>Sign out</button>
        </div>
      </header>
      <nav className="tabs">
        {[['leads', 'Leads'], ['companies', 'Companies'], ['tasks', 'Tasks'], ['search', 'Search']].map(([key, label]) => (
          <button key={key} className={tab === key ? 'tab active' : 'tab'}
            onClick={() => setTab(key)}>{label}</button>
        ))}
      </nav>
      {tab === 'leads' && (
        <LeadsView companies={companies} refreshKey={refreshKey}
          onChanged={() => setRefreshKey((k) => k + 1)} />
      )}
      {tab === 'companies' && <CompaniesView refreshKey={refreshKey} />}
      {tab === 'tasks' && <TasksView refreshKey={refreshKey} leads={leads} />}
      {tab === 'search' && <SearchView />}
    </main>
  )
}

function App() {
  const path = window.location.pathname
  if (path === '/workspace') return <Workspace />
  if (path === '/login') return <Login onDone={(needsPw) => { window.location.href = '/workspace' }} />
  return <Landing />
}

createRoot(document.getElementById('root')).render(<App />)
