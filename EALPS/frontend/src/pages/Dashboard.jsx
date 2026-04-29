import { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../App'
import api from '../api/client'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { TrendingUp, BookOpen, Target, Zap, ChevronRight, Plus } from 'lucide-react'

const ROLES = [
  'Full Stack Developer', 'Data Scientist', 'ML Engineer',
  'DevOps Engineer', 'Backend Developer', 'AI Engineer', 'Quantum Software Engineer'
]

function StatCard({ icon: Icon, label, value, color = 'brand' }) {
  return (
    <div className="glass rounded-xl p-5 flex items-center gap-4">
      <div className={`p-3 rounded-lg bg-${color}-500/15`}>
        <Icon size={22} className={`text-${color}-400`} />
      </div>
      <div>
        <div className="text-2xl font-bold text-white">{value}</div>
        <div className="text-sm text-slate-400">{label}</div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [pathways, setPathways]   = useState([])
  const [topSkills, setTopSkills] = useState([])
  const [showGen, setShowGen]     = useState(false)
  const [role, setRole]           = useState(ROLES[0])
  const [generating, setGenerating] = useState(false)

  useEffect(() => {
    api.get('/pathways/').then(r => setPathways(r.data)).catch(() => {})
    api.get('/skills/').then(r => {
      const sorted = r.data
        .filter(s => s.market?.demand_index)
        .sort((a,b) => (b.market?.demand_index||0) - (a.market?.demand_index||0))
        .slice(0, 8)
      setTopSkills(sorted)
    }).catch(() => {})
  }, [])

  const generatePathway = async () => {
    setGenerating(true)
    try {
      const { data } = await api.post('/pathways/generate', { target_role: role })
      setPathways(prev => [data, ...prev])
      navigate(`/roadmap/${data.pathway_id}`)
    } catch (e) {
      alert('Generation failed: ' + (e.response?.data?.error || e.message))
    } finally {
      setGenerating(false)
    }
  }

  const activePathway = pathways.find(p => p.status === 'active')

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white">
          Hello, {user?.full_name?.split(' ')[0]} 👋
        </h1>
        <p className="text-slate-400 mt-1">
          {user?.effort_capacity}h/week capacity · {user?.prior_skills?.length || 0} known skills
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={Target}   label="Active Pathways"  value={pathways.filter(p=>p.status==='active').length} />
        <StatCard icon={BookOpen} label="Total Pathways"   value={pathways.length} color="violet" />
        <StatCard icon={Zap}      label="Hours/Week"       value={user?.effort_capacity || 0} color="amber" />
        <StatCard icon={TrendingUp} label="Completion"
          value={activePathway ? `${activePathway.completion_percent}%` : '—'} color="green" />
      </div>

      {/* Active Pathway + Generate */}
      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 glass rounded-xl p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="font-semibold text-lg">Learning Pathways</h2>
            <button onClick={() => setShowGen(!showGen)}
              className="flex items-center gap-2 bg-brand-500 hover:bg-brand-600 text-white text-sm px-4 py-2 rounded-lg transition-colors">
              <Plus size={15} /> Generate New
            </button>
          </div>

          {showGen && (
            <div className="mb-5 p-4 bg-brand-500/10 border border-brand-500/20 rounded-xl space-y-3">
              <label className="block text-sm text-slate-300">Target Role</label>
              <select value={role} onChange={e => setRole(e.target.value)}
                className="w-full bg-slate-800 border border-white/10 rounded-lg px-3 py-2 text-white">
                {ROLES.map(r => <option key={r}>{r}</option>)}
              </select>
              <button onClick={generatePathway} disabled={generating}
                className="w-full bg-brand-500 hover:bg-brand-600 text-white py-2.5 rounded-lg font-medium transition-colors disabled:opacity-60">
                {generating ? 'Generating with FNN + Ollama…' : '⚡ Generate Pathway'}
              </button>
            </div>
          )}

          <div className="space-y-3">
            {pathways.length === 0 && (
              <div className="text-center py-12 text-slate-500">
                No pathways yet. Generate your first one!
              </div>
            )}
            {pathways.map(p => (
              <Link key={p.pathway_id} to={`/roadmap/${p.pathway_id}`}
                className="flex items-center justify-between p-4 bg-white/3 hover:bg-white/6 border border-white/5 rounded-xl transition-colors group">
                <div>
                  <div className="font-medium text-white">{p.target_role}</div>
                  <div className="text-sm text-slate-400 mt-0.5">
                    {p.total_estimated_hours}h total · {p.skills?.length || 0} skills · {p.completion_percent}% done
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`text-xs px-2 py-1 rounded-full ${
                    p.status === 'active'     ? 'bg-green-500/20 text-green-400' :
                    p.status === 'completed'  ? 'bg-blue-500/20 text-blue-400'  :
                    'bg-slate-500/20 text-slate-400'}`}>{p.status}</span>
                  <ChevronRight size={16} className="text-slate-500 group-hover:text-white transition-colors" />
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* Market Pulse */}
        <div className="glass rounded-xl p-6">
          <h2 className="font-semibold text-lg mb-5">Market Pulse</h2>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={topSkills} layout="vertical" margin={{ left: 0 }}>
              <XAxis type="number" domain={[0,100]} tick={{fontSize:11, fill:'#64748b'}} />
              <YAxis type="category" dataKey="skill_name" width={110} tick={{fontSize:11, fill:'#94a3b8'}} />
              <Tooltip
                contentStyle={{ background:'#1e293b', border:'1px solid #334155', borderRadius:8 }}
                labelStyle={{ color:'#e2e8f0' }}
                formatter={v => [`${v?.toFixed(1)} demand`, '']}
              />
              <Bar dataKey="market.demand_index" radius={4}>
                {topSkills.map((s, i) => (
                  <Cell key={i} fill={s.market?.emerging_flag ? '#22c55e' : s.market?.decay_flag ? '#ef4444' : '#4f6ef7'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div className="flex gap-4 text-xs text-slate-500 mt-3">
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-brand-500 inline-block"/>Normal</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500 inline-block"/>Emerging</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500 inline-block"/>Declining</span>
          </div>
        </div>
      </div>
    </div>
  )
}
