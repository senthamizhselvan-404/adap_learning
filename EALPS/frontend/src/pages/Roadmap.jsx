import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../App'
import api from '../api/client'
import {
  Clock, CheckCircle, Lock, PlayCircle,
  ChevronRight, RefreshCw, Calendar, Zap, TrendingUp,
} from 'lucide-react'

const DIFF_COLOR = { easy: '#22c55e', medium: '#f59e0b', hard: '#ef4444' }
const STATUS_ICON = {
  completed:   <CheckCircle size={16} className="text-green-400 flex-shrink-0" />,
  in_progress: <PlayCircle  size={16} className="text-brand-400 flex-shrink-0" />,
  locked:      <Lock        size={16} className="text-slate-500 flex-shrink-0" />,
}

// ─── Weekly schedule calculator ──────────────────────────────────────────────
function buildSchedule(skills, hoursPerWeek) {
  if (!hoursPerWeek || hoursPerWeek <= 0) hoursPerWeek = 10
  let cumulativeHours = 0
  return skills.map(ps => {
    if (ps.status === 'completed') {
      return { ...ps, weekStart: 0, weekEnd: 0, weekLabel: 'Completed' }
    }
    const startHours = cumulativeHours
    cumulativeHours += ps.estimated_hours
    const weekStart = Math.floor(startHours / hoursPerWeek) + 1
    const weekEnd   = Math.ceil(cumulativeHours / hoursPerWeek)
    const weekLabel = weekStart === weekEnd
      ? `Week ${weekStart}`
      : `Week ${weekStart}–${weekEnd}`
    return { ...ps, weekStart, weekEnd, weekLabel, cumulativeHours }
  })
}

function approxDate(weeksFromNow) {
  const d = new Date()
  d.setDate(d.getDate() + weeksFromNow * 7)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

// ─── Skill card ──────────────────────────────────────────────────────────────
function SkillCard({ ps, onLog }) {
  const [hours, setHours]   = useState('')
  const [loading, setLoading] = useState(false)
  const isFocused = ps.status === 'in_progress'
  const dc = DIFF_COLOR[ps.difficulty_label] || '#64748b'

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

      <div className="absolute -top-2 -left-2 w-6 h-6 rounded-full bg-slate-800 border border-white/10
        flex items-center justify-center text-xs font-bold text-slate-300">
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
          style={{ background: dc + '25', color: dc }}>
          {ps.difficulty_label}
        </span>
      </div>

      <div className="flex items-center gap-2 text-xs text-slate-400 mb-1">
        <Clock size={12} />
        <span>{ps.estimated_hours}h estimated</span>
        <span className="ml-auto">Bloom L{ps.bloom_level}</span>
      </div>

      {/* Week badge */}
      <div className="flex items-center gap-1 text-xs mb-3"
        style={{ color: ps.weekLabel === 'Completed' ? '#22c55e' : '#4f6ef7' }}>
        <Calendar size={11} />
        <span>{ps.weekLabel}</span>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-slate-800 rounded-full h-1 mb-3">
        <div className="h-1 rounded-full transition-all"
          style={{
            width:      ps.status === 'completed' ? '100%' : ps.status === 'in_progress' ? '30%' : '0%',
            background: dc,
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

// ─── Main Roadmap page ────────────────────────────────────────────────────────
export default function Roadmap() {
  const { id }   = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()

  const [pathway, setPathway]     = useState(null)
  const [pathways, setPathways]   = useState([])
  const [loading, setLoading]     = useState(true)
  const [recalibrating, setRecal] = useState(false)

  const effortCapacity = user?.effort_capacity || 10

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
      skill_id: skillId, hours_logged: hours,
    })
    setPathway(data)
  }, [pathway])

  const recalibrate = async () => {
    setRecal(true)
    const { data } = await api.post(`/pathways/${pathway.pathway_id}/recalibrate`)
    setPathway(data)
    setRecal(false)
  }

  if (loading) return (
    <div className="flex justify-center items-center h-64 text-slate-400">Loading…</div>
  )

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

  const skills        = pathway.skills || []
  const completed     = skills.filter(s => s.status === 'completed').length
  const total         = skills.length
  const scheduled     = buildSchedule(skills, effortCapacity)

  // Remaining (not completed) stats
  const remainingHours = skills
    .filter(s => s.status !== 'completed')
    .reduce((sum, s) => sum + s.estimated_hours, 0)
  const totalWeeks  = Math.ceil(remainingHours / effortCapacity)
  const endDate     = approxDate(totalWeeks)

  // Group skills by week for the timeline view
  const weekGroups = {}
  scheduled.forEach(ps => {
    const key = ps.weekLabel === 'Completed' ? 'done' : `${ps.weekStart}`
    if (!weekGroups[key]) weekGroups[key] = []
    weekGroups[key].push(ps)
  })
  const sortedWeekKeys = Object.keys(weekGroups).sort((a, b) => {
    if (a === 'done') return -1
    if (b === 'done') return 1
    return Number(a) - Number(b)
  })

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          {pathways.length > 1 && (
            <select value={pathway.pathway_id}
              onChange={e => navigate(`/roadmap/${e.target.value}`)}
              className="bg-slate-800 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-white mb-2">
              {pathways.map(p => (
                <option key={p.pathway_id} value={p.pathway_id}>{p.target_role}</option>
              ))}
            </select>
          )}
          <h1 className="text-3xl font-bold text-white">{pathway.target_role}</h1>
          <p className="text-slate-400 mt-1">
            {completed}/{total} skills completed ·{' '}
            <span className="text-brand-400 font-medium">{pathway.completion_percent}%</span> done
          </p>
        </div>

        <button onClick={recalibrate} disabled={recalibrating}
          className="flex items-center gap-2 glass border-white/10 hover:border-brand-500/40
            text-slate-300 text-sm px-4 py-2 rounded-lg transition-colors disabled:opacity-60">
          <RefreshCw size={14} className={recalibrating ? 'animate-spin' : ''} />
          Recalibrate
        </button>
      </div>

      {/* Overall progress bar */}
      <div className="w-full bg-slate-800 rounded-full h-2 mb-6">
        <div className="h-2 rounded-full bg-gradient-to-r from-brand-500 to-violet-500 transition-all"
          style={{ width: `${pathway.completion_percent}%` }} />
      </div>

      {/* Schedule summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
        <div className="glass rounded-xl p-4">
          <div className="flex items-center gap-2 text-slate-400 text-xs mb-1">
            <Clock size={12} /> Hours remaining
          </div>
          <div className="text-xl font-bold text-white">{remainingHours.toFixed(0)}h</div>
          <div className="text-xs text-slate-500 mt-0.5">of {pathway.total_estimated_hours}h total</div>
        </div>
        <div className="glass rounded-xl p-4">
          <div className="flex items-center gap-2 text-slate-400 text-xs mb-1">
            <Zap size={12} /> Weekly pace
          </div>
          <div className="text-xl font-bold text-white">{effortCapacity}h</div>
          <div className="text-xs text-slate-500 mt-0.5">per week</div>
        </div>
        <div className="glass rounded-xl p-4">
          <div className="flex items-center gap-2 text-slate-400 text-xs mb-1">
            <TrendingUp size={12} /> Duration
          </div>
          <div className="text-xl font-bold text-white">~{totalWeeks} week{totalWeeks !== 1 ? 's' : ''}</div>
          <div className="text-xs text-slate-500 mt-0.5">at current pace</div>
        </div>
        <div className="glass rounded-xl p-4">
          <div className="flex items-center gap-2 text-slate-400 text-xs mb-1">
            <Calendar size={12} /> Est. completion
          </div>
          <div className="text-base font-bold text-white">{totalWeeks > 0 ? endDate : 'Completed!'}</div>
          <div className="text-xs text-slate-500 mt-0.5">approximate</div>
        </div>
      </div>

      {/* Weekly timeline */}
      <div className="space-y-8">
        {sortedWeekKeys.map(weekKey => {
          const group        = weekGroups[weekKey]
          const isDone       = weekKey === 'done'
          const weekNum      = isDone ? 0 : Number(weekKey)
          const weekStart    = isDone ? '' : approxDate(weekNum - 1)
          const weekEnd      = isDone ? '' : approxDate(weekNum)
          const groupHours   = group.reduce((s, ps) => s + ps.estimated_hours, 0)

          return (
            <div key={weekKey}>
              {/* Week header */}
              <div className="flex items-center gap-3 mb-4">
                <div className={`flex-shrink-0 w-2 h-2 rounded-full ${isDone ? 'bg-green-500' : 'bg-brand-500'}`} />
                <div className="flex items-center gap-3 flex-wrap">
                  <span className={`font-semibold ${isDone ? 'text-green-400' : 'text-white'}`}>
                    {isDone ? 'Completed' : `Week ${weekKey}`}
                  </span>
                  {!isDone && (
                    <span className="text-xs text-slate-500">
                      {weekStart} – {weekEnd}
                    </span>
                  )}
                  <span className="text-xs text-slate-500">
                    · {groupHours.toFixed(0)}h · {group.length} skill{group.length !== 1 ? 's' : ''}
                  </span>
                </div>
                <div className="flex-1 h-px bg-white/5" />
              </div>

              {/* Skills in this week */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 ml-5">
                {group.map((ps, idx) => (
                  <div key={ps.id} className="relative">
                    <SkillCard ps={ps} onLog={logProgress} />
                    {idx < group.length - 1 && (
                      <div className="hidden xl:flex absolute -right-3 top-1/2 -translate-y-1/2 z-10">
                        <ChevronRight size={16} className="text-slate-700" />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )
        })}
      </div>

      {/* Pathway explanation from Ollama */}
      {pathway.explanation && !pathway.explanation.startsWith('[') && (
        <div className="mt-8 glass rounded-xl p-5 border border-brand-500/20">
          <div className="text-xs text-brand-400 font-medium mb-2 uppercase tracking-wider">
            gemma3:4b Pathway Insight
          </div>
          <p className="text-slate-300 text-sm leading-relaxed">{pathway.explanation}</p>
        </div>
      )}
    </div>
  )
}
