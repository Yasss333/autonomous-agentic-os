export class ApiError extends Error {
  constructor(status, detail, code) {
    super(detail || 'Request failed')
    this.status = status
    this.code = code
  }
}

let getSessionToken

export function setSessionTokenGetter(getToken) {
  getSessionToken = getToken
}

export async function apiFetch(path, { body, ...options } = {}) {
  const headers = new Headers()
  if (body !== undefined) headers.set('Content-Type', 'application/json')
  if (getSessionToken) {
    const token = await getSessionToken()
    if (!token) throw new ApiError(401, 'Not signed in')
    headers.set('Authorization', `Bearer ${token}`)
  }
  return fetch(`/api${path}`, {
    ...options,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
}

export async function api(path, options) {
  const response = await apiFetch(path, options)
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
