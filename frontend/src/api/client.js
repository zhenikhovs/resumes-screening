const TOKEN_KEY = 'access_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  const res = await fetch(path, { ...options, headers })
  if (res.status === 401) {
    clearToken()
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }
  const text = await res.text()
  let data = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = text
  }
  if (!res.ok) {
    const msg = data?.detail || (typeof data === 'string' ? data : res.statusText)
    throw new Error(Array.isArray(msg) ? msg.map((e) => e.msg).join(', ') : msg)
  }
  return data
}

export async function login(email, password) {
  const body = new URLSearchParams()
  body.append('username', email)
  body.append('password', password)
  const res = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })
  const text = await res.text()
  let data = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = text
  }
  if (!res.ok) {
    const msg = data?.detail || res.statusText
    throw new Error(Array.isArray(msg) ? msg.map((e) => e.msg).join(', ') : msg)
  }
  setToken(data.access_token)
  return data
}

export async function fetchMe() {
  return api('/api/auth/me')
}

export async function fetchMyInterviews() {
  return api('/api/auth/interviews')
}
