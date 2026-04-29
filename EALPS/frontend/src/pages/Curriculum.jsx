import { useState } from 'react'
import api from '../api/client'
import { FileText, Sparkles, CheckCircle, AlertCircle, BookOpen, Clock } from 'lucide-react'

export default function Curriculum() {
  const [title, setTitle]             = useState('')
  const [institution, setInstitution] = useState('')
  const [rawText, setRawText]         = useState('')
  const [result, setResult]           = useState(null)
  const [loading, setLoading]         = useState(false)
  const [error, setError]             = useState('')

  const DEMO_TEXT = `Course: Introduction to Machine Learning
Topics covered: Python programming, NumPy arrays, Pandas dataframes,
data preprocessing, feature engineering, linear regression, logistic regression,
decision trees, random forests, neural networks, model evaluation.

Course: Web Development Fundamentals
Topics: HTML5 semantics, CSS flexbox and grid, JavaScript ES6+, DOM manipulation,
React components, hooks, REST APIs, authentication, PostgreSQL basics.

Course: Cloud & DevOps
Topics: Docker containerization, Kubernetes orchestration, CI/CD pipelines,
AWS services (EC2, S3, RDS), Terraform infrastructure as code, monitoring.`

  const handleSubmit = async e => {
    e.preventDefault()
    if (!rawText.trim()) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const { data } = await api.post('/curriculum/', {
        title: title || 'Uploaded Curriculum',
        institution,
        raw_text: rawText,
      })
      setResult(data)
    } catch (err) {
      const msg = err.response?.data?.error || err.response?.data?.detail || 'Failed to process curriculum'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const DIFF_COLOR = { easy: '#22c55e', medium: '#f59e0b', hard: '#ef4444' }
  const diffLabel  = score => score < 0.35 ? 'Easy' : score < 0.65 ? 'Medium' : 'Hard'
  const diffColor  = score => score < 0.35 ? DIFF_COLOR.easy : score < 0.65 ? DIFF_COLOR.medium : DIFF_COLOR.hard

  const skills     = result?.extracted_skills ?? []
  const curriculum = result?.curriculum

  return (
    <div className="max-w-4xl mx-auto px-6 py-8 space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-white">Curriculum Analysis</h1>
        <p className="text-slate-400 mt-1">Paste curriculum content → gemma3:4b extracts skills → FNN scores difficulty</p>
      </div>

      <form onSubmit={handleSubmit} className="glass rounded-xl p-6 space-y-5">
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-slate-400 mb-1.5">Curriculum Title</label>
            <input value={title} onChange={e => setTitle(e.target.value)}
              placeholder="BTech CS Year 2 Curriculum"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1.5">Institution</label>
            <input value={institution} onChange={e => setInstitution(e.target.value)}
              placeholder="Takshashila University"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
            />
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="text-sm text-slate-400">Curriculum Content</label>
            <button type="button" onClick={() => setRawText(DEMO_TEXT)}
              className="text-xs text-brand-400 hover:text-brand-300">
              Load demo text
            </button>
          </div>
          <textarea value={rawText} onChange={e => setRawText(e.target.value)}
            rows={10} required
            placeholder="Paste syllabus, course descriptions, or any curriculum text here…"
            className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 font-mono resize-none"
          />
        </div>

        {error && (
          <div className="flex items-start gap-2 text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg p-3">
            <AlertCircle size={16} className="mt-0.5 flex-shrink-0" />
            <p className="text-sm">{error}</p>
          </div>
        )}

        <button type="submit" disabled={loading}
          className="flex items-center gap-2 bg-brand-500 hover:bg-brand-600 text-white font-semibold px-6 py-3 rounded-lg transition-colors disabled:opacity-60">
          <Sparkles size={16} />
          {loading ? 'Extracting with gemma3:4b…' : 'Analyse & Extract Skills'}
        </button>
      </form>

      {/* Results — always render when result is set */}
      {result && (
        <div className="space-y-6">

          {/* Curriculum metadata card */}
          <div className="glass rounded-xl p-5 flex items-start gap-4">
            <div className="p-3 rounded-lg bg-brand-500/15">
              <FileText size={20} className="text-brand-400" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <CheckCircle size={16} className="text-green-400 flex-shrink-0" />
                <span className="font-semibold text-white">{curriculum.title}</span>
              </div>
              {curriculum.institution && (
                <p className="text-sm text-slate-400">{curriculum.institution}</p>
              )}
              <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
                <span className="flex items-center gap-1">
                  <BookOpen size={12} />
                  {skills.length} skill{skills.length !== 1 ? 's' : ''} extracted
                </span>
                <span className="flex items-center gap-1">
                  <Clock size={12} />
                  {skills.reduce((s, sk) => s + (sk.avg_hours_to_learn || 20), 0).toFixed(0)}h total learning time
                </span>
              </div>
            </div>
          </div>

          {/* Ollama not running notice */}
          {skills.length === 0 && (
            <div className="glass rounded-xl p-5 border border-amber-500/20 bg-amber-500/5">
              <div className="flex items-start gap-3">
                <AlertCircle size={18} className="text-amber-400 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-amber-300 font-medium text-sm mb-1">No skills extracted</p>
                  <p className="text-slate-400 text-sm">
                    Ollama may not be running. Start it with:{' '}
                    <code className="text-brand-400 bg-white/5 px-1.5 py-0.5 rounded text-xs">ollama serve</code>
                  </p>
                  <p className="text-slate-500 text-xs mt-1">
                    Then pull the model:{' '}
                    <code className="text-brand-400 bg-white/5 px-1.5 py-0.5 rounded text-xs">ollama pull gemma3:4b</code>
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Skill cards */}
          {skills.length > 0 && (
            <>
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-white">Extracted Skills</h2>
                <div className="flex gap-3 text-xs text-slate-500">
                  {['easy','medium','hard'].map(d => (
                    <span key={d} className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full inline-block"
                        style={{ background: DIFF_COLOR[d] }} />
                      {d.charAt(0).toUpperCase() + d.slice(1)}
                    </span>
                  ))}
                </div>
              </div>

              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {skills.map((skill, i) => (
                  <div key={i} className="glass rounded-xl p-4 hover:border-white/20 transition-colors">
                    <div className="flex items-start justify-between mb-2">
                      <div className="font-semibold text-white text-sm leading-tight pr-2">
                        {skill.skill_name}
                      </div>
                      {skill.difficulty_score != null && (
                        <span className="text-xs px-2 py-0.5 rounded-full flex-shrink-0"
                          style={{
                            background: diffColor(skill.difficulty_score) + '20',
                            color:      diffColor(skill.difficulty_score),
                          }}>
                          {diffLabel(skill.difficulty_score)}
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-slate-400 space-y-1">
                      <div className="flex justify-between">
                        <span>Category</span>
                        <span className="text-slate-300 text-right max-w-[120px] truncate">{skill.category}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Bloom Level</span>
                        <span className="text-slate-300">L{skill.bloom_level}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Est. Hours</span>
                        <span className="text-slate-300">{skill.avg_hours_to_learn ?? 20}h</span>
                      </div>
                      <div className="flex justify-between">
                        <span>FNN Score</span>
                        <span style={{ color: skill.difficulty_score != null ? diffColor(skill.difficulty_score) : '#64748b' }}>
                          {skill.difficulty_score != null ? skill.difficulty_score.toFixed(3) : '—'}
                        </span>
                      </div>
                    </div>
                    {/* Difficulty bar */}
                    {skill.difficulty_score != null && (
                      <div className="mt-3 w-full bg-slate-800 rounded-full h-1">
                        <div className="h-1 rounded-full transition-all"
                          style={{
                            width:      `${skill.difficulty_score * 100}%`,
                            background: diffColor(skill.difficulty_score),
                          }} />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
