import axios from 'axios'

const api = axios.create({ baseURL: '/api/v1' })

// Attach token
api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('access_token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

// Auto-refresh on 401
api.interceptors.response.use(
  res => res,
  async err => {
    const original = err.config
    if (err.response?.status === 401 && !original._retry) {
      original._retry = true
      const refresh = localStorage.getItem('refresh_token')
      if (refresh) {
        try {
          const { data } = await axios.post('/api/v1/auth/refresh', {}, {
            headers: { Authorization: `Bearer ${refresh}` }
          })
          localStorage.setItem('access_token', data.access_token)
          original.headers.Authorization = `Bearer ${data.access_token}`
          return api(original)
        } catch {
          localStorage.clear()
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(err)
  }
)

// ──────────────────────────────────────
// Practice IDE API Methods
// ──────────────────────────────────────

export const practiceAPI = {
  // Get all practice problems with optional filters
  listProblems: (filters = {}) => {
    const params = new URLSearchParams()
    if (filters.skill_id) params.append('skill_id', filters.skill_id)
    if (filters.difficulty) params.append('difficulty', filters.difficulty)
    if (filters.language) params.append('language', filters.language)
    if (filters.page) params.append('page', filters.page)
    if (filters.per_page) params.append('per_page', filters.per_page)
    return api.get(`/practice/problems/?${params.toString()}`)
  },

  // Get a specific problem with test cases
  getProblem: (problemId) =>
    api.get(`/practice/problems/${problemId}`),

  // Execute code without saving
  executeProblem: (problemId, code, language) =>
    api.post(`/practice/problems/${problemId}/execute`, { code, language }),

  // Submit solution (saves and validates)
  submitProblem: (problemId, code, language) =>
    api.post(`/practice/problems/${problemId}/submit`, { code, language }),

  // Get practice sessions
  listSessions: (page = 1) =>
    api.get(`/practice/sessions/?page=${page}`),

  // Get session details
  getSession: (sessionId) =>
    api.get(`/practice/sessions/${sessionId}`),

  // Execute code in standalone IDE (no problem context)
  executeCode: (code, language) =>
    api.post('/practice/execute', { code, language }),
}

// ──────────────────────────────────────
// Admin Practice API Methods
// ──────────────────────────────────────

export const adminPracticeAPI = {
  // Create new problem
  createProblem: (problemData) =>
    api.post('/admin/practice/problems', problemData),

  // List all problems (admin view)
  listProblems: (page = 1) =>
    api.get(`/admin/practice/problems?page=${page}`),

  // Update problem
  updateProblem: (problemId, updates) =>
    api.patch(`/admin/practice/problems/${problemId}`, updates),

  // Delete problem
  deleteProblem: (problemId) =>
    api.delete(`/admin/practice/problems/${problemId}`),
}

export default api

