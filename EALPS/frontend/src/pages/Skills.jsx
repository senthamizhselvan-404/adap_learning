import { useEffect, useState } from 'react'
import api from '../api/client'
import { Search, TrendingUp, TrendingDown, Minus } from 'lucide-react'

const DIFF_COLOR = { easy: '#22c55e', medium: '#f59e0b', hard: '#ef4444' }

function diffLabel(score) {
  if (score == null) return { label: '—', color: '#64748b' }
  if (score < 0.35) return { label: 'Easy',   color: DIFF_COLOR.easy }
  if (score < 0.65) return { label: 'Medium', color: DIFF_COLOR.medium }
  return { label: 'Hard', color: DIFF_COLOR.hard }
}

function MarketBadge({ market }) {
  if (!market) return <span className="text-slate-600 text-xs">No data</span>
  if (market.emerging_flag) return (
    <span className="flex items-center gap-1 text-xs text-green-400">
      <TrendingUp size={12} /> Emerging
    </span>
  )
  if (market.decay_flag) return (
    <span className="flex items-center gap-1 text-xs text-red-400">
      <TrendingDown size={12} /> Declining
    </span>
  )
  return (
    <span className="flex items-center gap-1 text-xs text-slate-400">
      <Minus size={12} /> Stable
    </span>
  )
}

export default function Skills() {
  const [skills, setSkills]     = useState([])
  const [filtered, setFiltered] = useState([])
  const [search, setSearch]     = useState('')
  const [category, setCategory] = useState('All')
  const [categories, setCategories] = useState(['All'])
  const [loading, setLoading]   = useState(true)
  const [sort, setSort]         = useState('name')

  useEffect(() => {
    Promise.all([api.get('/skills/'), api.get('/skills/categories')]).then(([sr, cr]) => {
      setSkills(sr.data.skills)
      setFiltered(sr.data.skills)
      setCategories(['All', ...cr.data])
    }).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    let list = [...skills]
    if (category !== 'All') list = list.filter(s => s.category === category)
    if (search) list = list.filter(s => s.skill_name.toLowerCase().includes(search.toLowerCase()))
    if (sort === 'name')       list.sort((a,b) => a.skill_name.localeCompare(b.skill_name))
    if (sort === 'difficulty') list.sort((a,b) => (b.difficulty_score||0) - (a.difficulty_score||0))
    if (sort === 'demand')     list.sort((a,b) => (b.market?.demand_index||0) - (a.market?.demand_index||0))
    if (sort === 'hours')      list.sort((a,b) => b.avg_hours_to_learn - a.avg_hours_to_learn)
    setFiltered(list)
  }, [skills, search, category, sort])

  if (loading) return <div className="flex justify-center items-center h-64 text-slate-400">Loading skills…</div>

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">Skills Catalogue</h1>
          <p className="text-slate-400 mt-1">{filtered.length} skills · FNN-scored difficulty</p>
        </div>
      </div>

      {/* Filters */}
      <div className="glass rounded-xl p-4 mb-6 flex flex-wrap gap-4">
        <div className="flex-1 min-w-48 relative">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search skills…"
            className="w-full pl-9 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
          />
        </div>
        <select value={category} onChange={e => setCategory(e.target.value)}
          className="bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white">
          {categories.map(c => <option key={c} className="bg-slate-900">{c}</option>)}
        </select>
        <select value={sort} onChange={e => setSort(e.target.value)}
          className="bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white">
          <option value="name">Sort: Name</option>
          <option value="difficulty">Sort: Difficulty</option>
          <option value="demand">Sort: Demand</option>
          <option value="hours">Sort: Hours</option>
        </select>
      </div>

      {/* Skills grid */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {filtered.map(skill => {
          const diff = diffLabel(skill.difficulty_score)
          return (
            <div key={skill.skill_id} className="glass rounded-xl p-4 hover:border-white/20 transition-colors">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="font-semibold text-white text-sm leading-tight">{skill.skill_name}</div>
                  <div className="text-xs text-slate-500 mt-0.5">{skill.category}</div>
                </div>
                <span className="text-xs px-2 py-0.5 rounded-full ml-2 flex-shrink-0"
                  style={{ background: diff.color + '20', color: diff.color }}>
                  {diff.label}
                </span>
              </div>

              <div className="space-y-2 text-xs">
                <div className="flex justify-between text-slate-400">
                  <span>Bloom Level</span>
                  <span className="text-white font-medium">L{skill.bloom_level}/6</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Avg Hours</span>
                  <span className="text-white font-medium">{skill.avg_hours_to_learn}h</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Difficulty Score</span>
                  <span className="font-medium" style={{ color: diff.color }}>
                    {skill.difficulty_score != null ? skill.difficulty_score.toFixed(2) : '—'}
                  </span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Market Demand</span>
                  <span className="text-white font-medium">
                    {skill.market?.demand_index?.toFixed(1) ?? '—'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Trend</span>
                  <MarketBadge market={skill.market} />
                </div>
              </div>

              {/* Demand bar */}
              <div className="mt-3 w-full bg-slate-800 rounded-full h-1">
                <div className="h-1 rounded-full transition-all"
                  style={{
                    width: `${skill.market?.demand_index || 0}%`,
                    background: skill.market?.emerging_flag ? '#22c55e' :
                                skill.market?.decay_flag    ? '#ef4444' : '#4f6ef7'
                  }} />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
