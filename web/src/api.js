export class ApiError extends Error {
  constructor(status, detail, code) {
    super(detail || 'Request failed')
    this.status = status
    this.code = code
  }
}

export async function api(path, { method = 'GET', body } = {}) {
  const response = await fetch(`/api${path}`, {
    method,
    credentials: 'same-origin',
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (response.status === 204) return null
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new ApiError(response.status, data.detail, data.code)
  }
  return data
}

export const STAGES = ['new', 'contacted', 'qualified', 'customer', 'lost']
export const TASK_STATUSES = ['open', 'done', 'cancelled']
export const ACTIVITY_KINDS = ['note', 'call', 'email', 'meeting']

export function fmtDate(value) {
  if (!value) return '—'
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? value : d.toLocaleDateString()
}

export function fmtDateTime(value) {
  if (!value) return '—'
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString()
}
