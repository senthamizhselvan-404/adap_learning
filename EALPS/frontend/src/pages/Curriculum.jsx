import { useState } from 'react'
import api from '../api/client'
import { FileText, Sparkles, CheckCircle } from 'lucide-react'

export default function Curriculum() {
  const [title, setTitle]         = useState('')
  const [institution, setInstitution] = useState('')
  const [rawText, setRawText]     = useState('')
  const [result, setResult]       = useState(null)
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState('')

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
      setError(err.response?.data?.error || 'Failed to process curriculum')
    } finally {
      setLoading(false)
    }
  }

  const DIFF_COLOR = { easy: '#22c55e', medium: '#f59e0b', hard: '#ef4444' }
  const diffLabel = score => score < 0.35 ? 'Easy' : score < 0.65 ? 'Medium' : 'Hard'
  const diffColor = score => score < 0.35 ? DIFF_COLOR.easy : score < 0.65 ? DIFF_COLOR.medium : DIFF_COLOR.hard

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

        {error && <p className="text-red-400 text-sm">{error}</p>}

        <button type="submit" disabled={loading}
          className="flex items-center gap-2 bg-brand-500 hover:bg-brand-600 text-white font-semibold px-6 py-3 rounded-lg transition-colors disabled:opacity-60">
          <Sparkles size={16} />
          {loading ? 'Extracting with gemma3:4b…' : 'Analyse & Extract Skills'}
        </button>
      </form>

      {/* Results */}
      {result && (
        <div className="space-y-6 animate-in">
          <div className="flex items-center gap-2 text-green-400">
            <CheckCircle size={18} />
            <span className="font-medium">
              {result.extracted_skills.length} skills extracted from "{result.curriculum.title}"
            </span>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {result.extracted_skills.map((skill, i) => (
              <div key={i} className="glass rounded-xl p-4">
                <div className="flex items-start justify-between mb-2">
                  <div className="font-semibold text-white text-sm">{skill.skill_name}</div>
                  {skill.difficulty_score != null && (
                    <span className="text-xs px-2 py-0.5 rounded-full ml-2 flex-shrink-0"
                      style={{ background: diffColor(skill.difficulty_score) + '20', color: diffColor(skill.difficulty_score) }}>
                      {diffLabel(skill.difficulty_score)}
                    </span>
                  )}
                </div>
                <div className="text-xs text-slate-400 space-y-1">
                  <div className="flex justify-between">
                    <span>Category</span><span className="text-slate-300">{skill.category}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Bloom Level</span><span className="text-slate-300">L{skill.bloom_level}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>FNN Score</span>
                    <span style={{ color: skill.difficulty_score != null ? diffColor(skill.difficulty_score) : '#64748b' }}>
                      {skill.difficulty_score?.toFixed(3) ?? '—'}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {result.extracted_skills.length === 0 && (
            <div className="glass rounded-xl p-6 text-center text-slate-400">
              <p>No skills extracted. Ensure Ollama is running: <code className="text-brand-400">ollama serve</code></p>
              <p className="text-sm mt-1">Then pull the model: <code className="text-brand-400">ollama pull gemma3:4b</code></p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
