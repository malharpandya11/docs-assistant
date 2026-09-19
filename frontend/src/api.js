import { clearSession, getToken } from './auth'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function request(path, options = {}) {
  const token = getToken()
  const headers = { ...(options.headers || {}) }
  if (token) headers.Authorization = `Bearer ${token}`

  const res = await fetch(`${API_URL}${path}`, { ...options, headers })

  if (res.status === 401) {
    // Token expired/invalid — there's nothing a retry can fix, so drop the
    // stale session rather than let every subsequent call fail the same way.
    clearSession()
  }

  const body = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(body.detail || `Request failed (${res.status})`)
  }
  return body
}

export async function register(email, password) {
  return request('/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
}

export async function login(email, password) {
  return request('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
}

export async function logout() {
  return request('/auth/logout', { method: 'POST' })
}

export async function sendChat(question, conversationId) {
  return request('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, conversation_id: conversationId }),
  })
}

export async function uploadDocument(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request('/upload', { method: 'POST', body: formData })
}

export async function listConversations() {
  return request('/conversations')
}

export async function getConversation(id) {
  return request(`/conversations/${id}`)
}

export async function deleteConversation(id) {
  return request(`/conversations/${id}`, { method: 'DELETE' })
}
