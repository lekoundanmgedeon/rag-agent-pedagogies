/**
 * Service API — unique point de contact avec le backend FastAPI (agent-tuteur-api).
 *
 * Contrat : authentification JWT `Bearer` (cf. /api/auth/login). Le streaming du
 * chat et du statut d'ingestion utilise `fetch` (et non EventSource) afin de
 * pouvoir porter l'en-tête Authorization ; le format SSE du backend est
 * `data: {json}` où json contient l'une des clés meta / token / done / error.
 */

import axios from 'axios'

const TOKEN_KEY = 'tuteur_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}
export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

const http = axios.create({ baseURL: '/', timeout: 30_000 })

http.interceptors.request.use((cfg) => {
  const token = getToken()
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

// Déconnexion automatique sur 401 (jeton expiré/invalide) — sauf sur /login.
http.interceptors.response.use(
  (r) => r,
  (error) => {
    const status = error?.response?.status
    const url = error?.config?.url || ''
    if (status === 401 && !url.includes('/auth/login')) {
      clearToken()
      if (!location.pathname.startsWith('/login')) location.assign('/login')
    }
    return Promise.reject(error)
  },
)

export function apiErrorMessage(error, fallback = 'Une erreur est survenue.') {
  return error?.response?.data?.detail || error?.message || fallback
}

// ── Auth ─────────────────────────────────────────────────────────────────────
export const authApi = {
  login: (email, password) => http.post('/api/auth/login', { email, password }),
  me: () => http.get('/api/auth/me'),
  listUsers: () => http.get('/api/auth/users'),
  createUser: (payload) => http.post('/api/auth/users', payload),
}

// ── Chat (SSE via fetch) ─────────────────────────────────────────────────────
/**
 * Ouvre le flux SSE de /api/chat et yield les événements décodés.
 * @returns {AsyncGenerator<{meta?,token?,done?,error?}>}
 */
export async function* streamChat({ question, conversationId, curriculumContext, studentId, signal }) {
  const body = { question, curriculum_context: curriculumContext || {} }
  if (conversationId) body.conversation_id = conversationId
  if (studentId) body.student_id = studentId

  const resp = await fetch('/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      Authorization: `Bearer ${getToken()}`,
    },
    body: JSON.stringify(body),
    signal,
  })

  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`
    try {
      detail = (await resp.json()).detail || detail
    } catch { /* corps non-JSON */ }
    const err = new Error(detail)
    err.status = resp.status
    throw err
  }

  yield* parseSSE(resp.body)
}

/** Parse un ReadableStream SSE (`data: {json}`) en événements JSON. */
export async function* parseSSE(stream) {
  const reader = stream.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split(/\r?\n/)
      buffer = lines.pop() ?? ''
      for (const line of lines) {
        if (!line.startsWith('data:')) continue
        const data = line.slice(5).trim()
        if (!data) continue
        try {
          yield JSON.parse(data)
        } catch { /* fragment JSON incomplet */ }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

// ── Conversations ────────────────────────────────────────────────────────────
export const conversationsApi = {
  // student_id optionnel : requis seulement pour un admin inspectant un élève.
  list: (studentId) => http.get('/api/conversations', { params: studentId ? { student_id: studentId } : {} }),
  messages: (id) => http.get(`/api/conversations/${id}/messages`),
  remove: (id) => http.delete(`/api/conversations/${id}`),
}

// ── Feedback ─────────────────────────────────────────────────────────────────
export const feedbackApi = {
  submit: (messageId, value) => http.post(`/api/messages/${messageId}/feedback`, { value }),
}

// ── Progression ──────────────────────────────────────────────────────────────
export const progressionApi = {
  get: (studentId) => http.get(`/api/progression/${encodeURIComponent(studentId)}`),
}

// ── Documents (admin) ────────────────────────────────────────────────────────
export const documentsApi = {
  list: () => http.get('/api/documents'),
  get: (id) => http.get(`/api/documents/${id}`),
  remove: (id) => http.delete(`/api/documents/${id}`),
  verifyAll: () => http.post('/api/documents/verify-all'),

  upload(files, metadata = {}, onProgress) {
    const form = new FormData()
    for (const file of files) form.append('files', file)
    for (const [k, v] of Object.entries(metadata)) if (v) form.append(k, v)
    return http.post('/api/documents', form, {
      onUploadProgress: (e) => {
        if (e.total) onProgress?.(Math.round((e.loaded / e.total) * 100))
      },
    })
  },

  reindex(id, file) {
    const form = new FormData()
    form.append('file', file)
    return http.post(`/api/documents/${id}/reindex`, form)
  },

  /** Suit le statut d'indexation via SSE (fetch GET + Bearer). Retourne un annuleur. */
  watchStatus(id, onEvent) {
    const controller = new AbortController()
    ;(async () => {
      try {
        const resp = await fetch(`/api/documents/${id}/status`, {
          headers: { Authorization: `Bearer ${getToken()}`, Accept: 'text/event-stream' },
          signal: controller.signal,
        })
        if (!resp.ok || !resp.body) return
        for await (const evt of parseSSE(resp.body)) onEvent(evt)
      } catch { /* flux interrompu (annulation/erreur réseau) */ }
    })()
    return () => controller.abort()
  },
}

// ── Search (admin) ───────────────────────────────────────────────────────────
export const searchApi = {
  search: (query, curriculumContext = {}, topK = 5) =>
    http.post('/api/search', { query, curriculum_context: curriculumContext, top_k: topK }),
}

// ── Logs (admin) ─────────────────────────────────────────────────────────────
export const logsApi = {
  chat: (limit = 50) => http.get('/api/logs/chat', { params: { limit } }),
}

// ── Health ───────────────────────────────────────────────────────────────────
export const healthApi = {
  get: () => http.get('/health'),
}
