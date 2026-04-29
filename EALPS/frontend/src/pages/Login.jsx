import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../App'
import api from '../api/client'

export default function Login() {
  const { login } = useAuth()
  const [form, setForm]   = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async e => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const { data } = await api.post('/auth/login', form)
      login({ access_token: data.access_token, refresh_token: data.refresh_token }, data.learner)
    } catch (err) {
      setError(err.response?.data?.error || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        <div className="text-center mb-10">
          <div className="text-5xl mb-4">⬡</div>
          <h1 className="text-3xl font-bold text-white">EALPS</h1>
          <p className="text-slate-400 mt-2">Effort-Aware Adaptive Learning</p>
        </div>

        <form onSubmit={handleSubmit} className="glass rounded-2xl p-8 space-y-5">
          <div>
            <label className="block text-sm text-slate-400 mb-1.5">Email</label>
            <input
              type="email" value={form.email} required
              onChange={e => setForm({...form, email: e.target.value})}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 transition-colors"
              placeholder="admin@ealps.dev"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1.5">Password</label>
            <input
              type="password" value={form.password} required
              onChange={e => setForm({...form, password: e.target.value})}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-brand-500 transition-colors"
              placeholder="••••••••"
            />
          </div>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <button type="submit" disabled={loading}
            className="w-full bg-brand-500 hover:bg-brand-600 text-white font-semibold py-3 rounded-lg transition-colors disabled:opacity-60">
            {loading ? 'Signing in…' : 'Sign In'}
          </button>

          <p className="text-center text-slate-400 text-sm">
            No account? <Link to="/register" className="text-brand-400 hover:underline">Register</Link>
          </p>
          <div className="text-xs text-slate-600 text-center border-t border-white/5 pt-4">
            Demo: admin@ealps.dev / admin123 &nbsp;|&nbsp; learner@ealps.dev / learner123
          </div>
        </form>
      </div>
    </div>
  )
}
