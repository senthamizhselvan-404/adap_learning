import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../App'
import api from '../api/client'

const ROLES = ['Full Stack Developer', 'Data Scientist', 'ML Engineer', 'DevOps Engineer',
               'Backend Developer', 'AI Engineer', 'Quantum Software Engineer']

export default function Register() {
  const { login } = useAuth()
  const [form, setForm] = useState({
    full_name: '', email: '', password: '',
    effort_capacity: 10, prior_skills: ''
  })
  const [error, setError]   = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async e => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const payload = {
        ...form,
        effort_capacity: Number(form.effort_capacity),
        prior_skills: form.prior_skills.split(',').map(s => s.trim()).filter(Boolean),
      }
      const { data } = await api.post('/auth/register', payload)
      login({ access_token: data.access_token, refresh_token: data.refresh_token }, data.learner)
    } catch (err) {
      setError(err.response?.data?.error || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  const field = (label, key, type = 'text', extra = {}) => (
    <div>
      <label className="block text-sm text-slate-400 mb-1.5">{label}</label>
      <input type={type} value={form[key]} required
        onChange={e => setForm({...form, [key]: e.target.value})}
        className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 transition-colors"
        {...extra}
      />
    </div>
  )

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="text-5xl mb-3">⬡</div>
          <h1 className="text-2xl font-bold">Create Account</h1>
        </div>
        <form onSubmit={handleSubmit} className="glass rounded-2xl p-8 space-y-4">
          {field('Full Name', 'full_name', 'text', { placeholder: 'Your name' })}
          {field('Email', 'email', 'email', { placeholder: 'you@email.com' })}
          {field('Password', 'password', 'password', { placeholder: '••••••••' })}

          <div>
            <label className="block text-sm text-slate-400 mb-1.5">Hours available per week</label>
            <input type="number" min="1" max="80" value={form.effort_capacity}
              onChange={e => setForm({...form, effort_capacity: e.target.value})}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-brand-500"
            />
          </div>

          <div>
            <label className="block text-sm text-slate-400 mb-1.5">Skills you already know (comma-separated)</label>
            <input type="text" value={form.prior_skills}
              onChange={e => setForm({...form, prior_skills: e.target.value})}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
              placeholder="HTML, CSS, Python"
            />
          </div>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <button type="submit" disabled={loading}
            className="w-full bg-brand-500 hover:bg-brand-600 text-white font-semibold py-3 rounded-lg transition-colors disabled:opacity-60">
            {loading ? 'Creating account…' : 'Get Started'}
          </button>
          <p className="text-center text-slate-400 text-sm">
            Already have an account? <Link to="/login" className="text-brand-400 hover:underline">Sign in</Link>
          </p>
        </form>
      </div>
    </div>
  )
}
