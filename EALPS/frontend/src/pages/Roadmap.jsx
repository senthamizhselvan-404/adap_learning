import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../api/client'
import { Clock, CheckCircle, Lock, PlayCircle, ChevronRight, RefreshCw } from 'lucide-react'

const DIFF_COLOR = { easy: '#22c55e', medium: '#f59e0b', hard: '#ef4444' }
const STATUS_ICON = {
  completed:   <CheckCircle size={16} className="text-green-400" />,
  in_progress: <PlayCircle  size={16} className="text-brand-400" />,
  locked:      <Lock        size={16} className="text-slate-500" />,
}

function SkillCard({ ps, onLog }) {
  const [hours, setHours] = useState('')
  const [loading, setLoading] = useState(false)
  const isFocused = ps.status === 'in_progress'

  const logHours = async () => {
    if (!hours || ps.status === 'locked') return
    setLoading(true)
    try { await onLog(ps.skill_id, Number(hours)); setHours('') }
    finally { setLoading(false) }
  }

  return (
    <div className={`relative glass rounded-xl p-4 border transition-all
      ${isFocused ? 'border-brand-500/40 shadow-lg shadow-brand-500/10' : 'border-white/5'}
      ${ps.status === 'locked' ? 'opacity-50' : ''}`}>

      {/* Sequence badge */}
      <div className="absolute -top-2 -left-2 w-6 h-6 rounded-full bg-slate-800 border border-white/10 flex items-center justify-center text-xs font-bold text-slate-300">
        {ps.sequence_order}
      </div>

      <div className="flex items-start justify-between mb-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            {STATUS_ICON[ps.status]}
            <span className="font-semibold text-white text-sm truncate">{ps.skill_name}</span>
          </div>
          <div className="text-xs text-slate-400 mt-0.5">{ps.category}</div>
        </div>
        <span className="text-xs px-2 py-0.5 rounded-full ml-2 flex-shrink-0"
          style={{ background: DIFF_COLOR[ps.difficulty_label] + '25', color: DIFF_COLOR[ps.difficulty_label] }}>
          {ps.difficulty_label}
        </span>
      </div>

      <div className="flex items-center gap-2 text-xs text-slate-400 mb-3">
        <Clock size={12} />
        <span>{ps.estimated_hours}h estimated</span>
        <span className="ml-auto">Bloom L{ps.bloom_level}</span>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-slate-800 rounded-full h-1 mb-3">
        <div className="h-1 rounded-full transition-all"
          style={{
            width: ps.status === 'completed' ? '100%' : ps.status === 'in_progress' ? '30%' : '0%',
            background: DIFF_COLOR[ps.difficulty_label]
          }} />
      </div>

      {isFocused && (
        <div className="flex gap-2 mt-2">
          <input type="number" min="0.5" step="0.5" value={hours}
            onChange={e => setHours(e.target.value)}
            placeholder="Hours spent"
            className="flex-1 bg-slate-800 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
          />
          <button onClick={logHours} disabled={loading || !hours}
            className="bg-brand-500 hover:bg-brand-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-60">
            {loading ? '…' : 'Log'}
          </button>
        </div>
      )}
    </div>
  )
}

export default function Roadmap() {
  const { id }  = useParams()
  const navigate = useNavigate()
  const [pathway, setPathway]   = useState(null)
  const [pathways, setPathways] = useState([])
  const [loading, setLoading]   = useState(true)
  const [recalibrating, setRecalibrating] = useState(false)

  useEffect(() => {
    api.get('/pathways/').then(r => {
      setPathways(r.data)
      const target = id ? r.data.find(p => p.pathway_id === id) : r.data[0]
      if (target) {
        api.get(`/pathways/${target.pathway_id}`).then(res => setPathway(res.data))
      }
    }).finally(() => setLoading(false))
  }, [id])

  const logProgress = useCallback(async (skillId, hours) => {
    if (!pathway) return
    const { data } = await api.put(`/pathways/${pathway.pathway_id}/progress`, {
      skill_id: skillId, hours_logged: hours
    })
    setPathway(data)
  }, [pathway])

  const recalibrate = async () => {
    setRecalibrating(true)
    const { data } = await api.post(`/pathways/${pathway.pathway_id}/recalibrate`)
    setPathway(data)
    setRecalibrating(false)
  }

  if (loading) return <div className="flex justify-center items-center h-64 text-slate-400">Loading…</div>

  if (!pathway) return (
    <div className="max-w-2xl mx-auto px-6 py-16 text-center">
      <div className="text-5xl mb-4">🗺️</div>
      <h2 className="text-xl font-semibold text-white mb-2">No Pathway Yet</h2>
      <p className="text-slate-400 mb-6">Generate your first learning pathway from the Dashboard.</p>
      <button onClick={() => navigate('/dashboard')}
        className="bg-brand-500 hover:bg-brand-600 text-white px-6 py-3 rounded-lg font-medium">
        Go to Dashboard
      </button>
    </div>
  )

  const completed = pathway.skills?.filter(s => s.status === 'completed').length || 0
  const total     = pathway.skills?.length || 0

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <div className="flex items-center gap-3 mb-1">
            {pathways.length > 1 && (
              <select value={pathway.pathway_id}
                onChange={e => navigate(`/roadmap/${e.target.value}`)}
                className="bg-slate-800 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-white">
                {pathways.map(p => <option key={p.pathway_id} value={p.pathway_id}>{p.target_role}</option>)}
              </select>
            )}
          </div>
          <h1 className="text-3xl font-bold text-white">{pathway.target_role}</h1>
          <p className="text-slate-400 mt-1">
            {completed}/{total} skills completed · {pathway.total_estimated_hours}h total ·{' '}
            <span className="text-brand-400 font-medium">{pathway.completion_percent}%</span>
          </p>
        </div>

        <button onClick={recalibrate} disabled={recalibrating}
          className="flex items-center gap-2 glass border-white/10 hover:border-brand-500/40 text-slate-300 text-sm px-4 py-2 rounded-lg transition-colors disabled:opacity-60">
          <RefreshCw size={14} className={recalibrating ? 'animate-spin' : ''} />
          Recalibrate
        </button>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-slate-800 rounded-full h-2 mb-8">
        <div className="h-2 rounded-full bg-gradient-to-r from-brand-500 to-violet-500 transition-all"
          style={{ width: `${pathway.completion_percent}%` }} />
      </div>

      {/* Skills grid — directed flow layout */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {pathway.skills?.map((ps, idx) => (
          <div key={ps.id} className="relative">
            <SkillCard ps={ps} onLog={logProgress} />
            {/* Arrow to next */}
            {idx < pathway.skills.length - 1 && (
              <div className="hidden xl:flex absolute -right-3 top-1/2 -translate-y-1/2 z-10 items-center">
                <ChevronRight size={16} className="text-slate-600" />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Pathway explanation from Ollama */}
      {pathway.explanation && !pathway.explanation.startsWith('[') && (
        <div className="mt-8 glass rounded-xl p-5 border-brand-500/20">
          <div className="text-xs text-brand-400 font-medium mb-2 uppercase tracking-wider">
            🤖 gemma3:4b Pathway Insight
          </div>
          <p className="text-slate-300 text-sm leading-relaxed">{pathway.explanation}</p>
        </div>
      )}
    </div>
  )
}
