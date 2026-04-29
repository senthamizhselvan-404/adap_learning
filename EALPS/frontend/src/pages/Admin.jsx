import { useEffect, useState } from 'react'
import api from '../api/client'
import { RefreshCw, TrendingDown, TrendingUp, Users, BookOpen, Map, Activity } from 'lucide-react'

export default function Admin() {
  const [health, setHealth]   = useState(null)
  const [stats, setStats]     = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [refreshing, setRefreshing] = useState(false)
  const [analysing,  setAnalysing]  = useState(false)
  const [addForm, setAddForm] = useState({ skill_name: '', category: 'Programming', bloom_level: 3, avg_hours_to_learn: 20 })
  const [addMsg, setAddMsg]   = useState('')

  const load = () => Promise.all([
    api.get('/admin/curriculum/health').then(r => setHealth(r.data)).catch(() => {}),
    api.get('/admin/stats').then(r => setStats(r.data)).catch(() => {}),
  ])

  useEffect(() => { load() }, [])

  const refreshMarket = async () => {
    setRefreshing(true)
    await api.post('/admin/market/refresh').catch(() => {})
    await load()
    setRefreshing(false)
  }

  const runAnalysis = async () => {
    setAnalysing(true)
    const { data } = await api.get('/admin/curriculum/analysis').catch(() => ({ data: null }))
    setAnalysis(data)
    setAnalysing(false)
  }

  const addSkill = async e => {
    e.preventDefault()
    try {
      await api.post('/admin/skills', { ...addForm, bloom_level: Number(addForm.bloom_level), avg_hours_to_learn: Number(addForm.avg_hours_to_learn) })
      setAddMsg('✓ Skill added successfully')
      setAddForm({ skill_name: '', category: 'Programming', bloom_level: 3, avg_hours_to_learn: 20 })
    } catch(err) {
      setAddMsg('Error: ' + (err.response?.data?.error || err.message))
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-white">Admin Dashboard</h1>
        <button onClick={refreshMarket} disabled={refreshing}
          className="flex items-center gap-2 bg-brand-500 hover:bg-brand-600 text-white px-4 py-2.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-60">
          <RefreshCw size={15} className={refreshing ? 'animate-spin' : ''} />
          Refresh Market Data
        </button>
      </div>

      {/* System KPIs */}
      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { icon: Users,   label: 'Total Learners',  value: stats.total_learners  },
            { icon: BookOpen,label: 'Total Skills',    value: stats.total_skills    },
            { icon: Map,     label: 'Total Pathways',  value: stats.total_pathways  },
            { icon: Activity,label: 'Active Pathways', value: stats.active_pathways },
          ].map(({ icon: Icon, label, value }) => (
            <div key={label} className="glass rounded-xl p-5 flex items-center gap-4">
              <div className="p-3 rounded-lg bg-brand-500/10"><Icon size={20} className="text-brand-400" /></div>
              <div>
                <div className="text-2xl font-bold text-white">{value}</div>
                <div className="text-sm text-slate-400">{label}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Curriculum Health */}
      {health && (
        <div className="grid lg:grid-cols-4 gap-4">
          {[
            { label: 'Active Skills', value: health.kpis.total_active_skills, color: 'text-white' },
            { label: 'Decaying', value: health.kpis.skills_with_decay, color: 'text-red-400' },
            { label: 'Emerging', value: health.kpis.emerging_skills, color: 'text-green-400' },
            { label: 'Coverage Score', value: `${health.kpis.coverage_score}%`, color: 'text-brand-400' },
          ].map(({ label, value, color }) => (
            <div key={label} className="glass rounded-xl p-5 text-center">
              <div className={`text-3xl font-bold mb-1 ${color}`}>{value}</div>
              <div className="text-sm text-slate-400">{label}</div>
            </div>
          ))}
        </div>
      )}

      {health && (
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Decaying Skills */}
          <div className="glass rounded-xl p-6">
            <div className="flex items-center gap-2 mb-4">
              <TrendingDown size={18} className="text-red-400" />
              <h2 className="font-semibold text-white">Declining Skills</h2>
            </div>
            <div className="space-y-2">
              {health.decayed_skills.slice(0,8).map((s,i) => (
                <div key={i} className="flex items-center justify-between py-2 border-b border-white/5">
                  <div>
                    <div className="text-sm text-white font-medium">{s.name}</div>
                    <div className="text-xs text-slate-500">{s.category}</div>
                  </div>
                  <span className="text-xs text-red-400 font-mono">{s.demand?.toFixed(1)}</span>
                </div>
              ))}
              {health.decayed_skills.length === 0 && <p className="text-slate-500 text-sm">No declining skills detected.</p>}
            </div>
          </div>

          {/* Emerging Skills */}
          <div className="glass rounded-xl p-6">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp size={18} className="text-green-400" />
              <h2 className="font-semibold text-white">Emerging Skills</h2>
            </div>
            <div className="space-y-2">
              {health.emerging_skills.slice(0,8).map((s,i) => (
                <div key={i} className="flex items-center justify-between py-2 border-b border-white/5">
                  <div>
                    <div className="text-sm text-white font-medium">{s.name}</div>
                    <div className="text-xs text-slate-500">{s.category}</div>
                  </div>
                  <span className="text-xs text-green-400 font-mono">{s.demand?.toFixed(1)}</span>
                </div>
              ))}
              {health.emerging_skills.length === 0 && <p className="text-slate-500 text-sm">No emerging skills detected.</p>}
            </div>
          </div>
        </div>
      )}

      {/* Ollama AI Analysis */}
      <div className="glass rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-white">🤖 AI Curriculum Analysis (gemma3:4b)</h2>
          <button onClick={runAnalysis} disabled={analysing}
            className="text-sm bg-violet-500/20 hover:bg-violet-500/30 text-violet-300 px-4 py-2 rounded-lg transition-colors disabled:opacity-60">
            {analysing ? 'Analysing with Ollama…' : 'Run Analysis'}
          </button>
        </div>
        {analysis ? (
          <div className="space-y-2">
            <p className="text-slate-300 text-sm leading-relaxed whitespace-pre-line">{analysis.analysis}</p>
          </div>
        ) : (
          <p className="text-slate-500 text-sm">Click "Run Analysis" to get AI-generated curriculum recommendations from gemma3:4b.</p>
        )}
      </div>

      {/* Add Skill */}
      <div className="glass rounded-xl p-6">
        <h2 className="font-semibold text-white mb-4">Add New Skill</h2>
        <form onSubmit={addSkill} className="grid sm:grid-cols-2 gap-4">
          {[
            { label: 'Skill Name', key: 'skill_name', type: 'text' },
            { label: 'Category',   key: 'category',   type: 'text' },
          ].map(({ label, key, type }) => (
            <div key={key}>
              <label className="block text-xs text-slate-400 mb-1">{label}</label>
              <input type={type} value={addForm[key]} required
                onChange={e => setAddForm({...addForm, [key]: e.target.value})}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-brand-500"
              />
            </div>
          ))}
          <div>
            <label className="block text-xs text-slate-400 mb-1">Bloom Level (1–6)</label>
            <input type="number" min="1" max="6" value={addForm.bloom_level}
              onChange={e => setAddForm({...addForm, bloom_level: e.target.value})}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-brand-500"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Avg Hours to Learn</label>
            <input type="number" min="1" value={addForm.avg_hours_to_learn}
              onChange={e => setAddForm({...addForm, avg_hours_to_learn: e.target.value})}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-brand-500"
            />
          </div>
          <div className="sm:col-span-2 flex items-center gap-4">
            <button type="submit"
              className="bg-brand-500 hover:bg-brand-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition-colors">
              Add Skill
            </button>
            {addMsg && <span className={`text-sm ${addMsg.startsWith('✓') ? 'text-green-400' : 'text-red-400'}`}>{addMsg}</span>}
          </div>
        </form>
      </div>
    </div>
  )
}
