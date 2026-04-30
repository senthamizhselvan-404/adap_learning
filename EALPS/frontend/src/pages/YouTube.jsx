import { useState, useEffect, useRef, useCallback } from 'react'
import { Youtube, Clock, BookOpen, CheckCircle, Play } from 'lucide-react'
import api from '../api/client'

// ── YouTube IFrame API loader (singleton) ─────────────────────────────────────
const ytCallbacks = []
let ytScriptQueued = false

function loadYTApi(cb) {
  if (window.YT?.Player) { cb(); return }
  ytCallbacks.push(cb)
  if (!ytScriptQueued) {
    ytScriptQueued = true
    const tag = document.createElement('script')
    tag.src = 'https://www.youtube.com/iframe_api'
    document.head.appendChild(tag)
    window.onYouTubeIframeAPIReady = () => {
      ytCallbacks.forEach(fn => fn())
      ytCallbacks.length = 0
    }
  }
}

// ── Extract video ID from URL or bare ID ─────────────────────────────────────
function extractId(raw) {
  if (!raw) return null
  const s = raw.trim()
  if (/^[a-zA-Z0-9_-]{11}$/.test(s)) return s
  const m = s.match(/(?:youtube\.com\/(?:watch\?v=|embed\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/)
  return m ? m[1] : null
}

// ── Skill confidence bar ──────────────────────────────────────────────────────
function SkillBar({ skillData, status }) {
  const conf = skillData ? Math.round(skillData.confidence * 100) : 0
  const hasSkill = skillData?.is_relevant && skillData.confidence >= 0.6

  return (
    <div className="flex items-center gap-3 px-4 py-3 bg-slate-900 border-t border-slate-800 min-h-[52px]">
      <span className="text-xs text-slate-500 uppercase tracking-widest shrink-0">Skill</span>

      {hasSkill ? (
        <>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-violet-900/40 border border-violet-700 rounded-full text-xs font-medium text-violet-300">
            <span className="w-1.5 h-1.5 rounded-full bg-violet-400" />
            {skillData.matched_skill}
          </span>
          <div className="flex items-center gap-2 ml-auto text-xs text-slate-500 shrink-0">
            <div className="w-16 h-1 bg-slate-700 rounded-full overflow-hidden">
              <div className="h-full bg-violet-500 rounded-full transition-all duration-500" style={{ width: `${conf}%` }} />
            </div>
            {conf}% match
          </div>
        </>
      ) : (
        <span className={`text-xs ml-auto ${status?.startsWith('✓') ? 'text-green-400' : 'text-slate-500'}`}>
          {status || 'Detecting…'}
        </span>
      )}

      {hasSkill && status && (
        <span className={`text-xs shrink-0 ${status.startsWith('✓') ? 'text-green-400' : 'text-slate-500'}`}>
          {status}
        </span>
      )}
    </div>
  )
}

// ── Watch history row ─────────────────────────────────────────────────────────
function HistoryRow({ track, onReload }) {
  return (
    <div
      className="flex items-center gap-4 p-3 bg-slate-900 rounded-lg border border-slate-800 hover:border-slate-600 transition-colors cursor-pointer group"
      onClick={() => onReload(track.video_id)}
    >
      <div className="w-8 h-8 rounded-md bg-slate-800 flex items-center justify-center shrink-0 group-hover:bg-violet-900/40 transition-colors">
        <Play size={13} className="text-slate-500 group-hover:text-violet-400" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-200 truncate">
          {track.video_title || track.video_id}
        </p>
        {track.skill_name && (
          <p className="text-xs text-violet-400 flex items-center gap-1 mt-0.5">
            <BookOpen size={11} /> {track.skill_name}
          </p>
        )}
      </div>
      <div className="flex items-center gap-3 text-xs text-slate-500 shrink-0">
        <span className="flex items-center gap-1">
          <Clock size={11} /> {track.watched_minutes} min
        </span>
        {track.is_completed && <CheckCircle size={14} className="text-green-400" />}
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function YouTube() {
  const [urlInput, setUrlInput]   = useState('')
  const [videoId,  setVideoId]    = useState(null)
  const [skillData, setSkillData] = useState(null)
  const [status,   setStatus]     = useState('')
  const [history,  setHistory]    = useState([])
  const [histLoading, setHistLoading] = useState(true)

  const playerRef    = useRef(null)
  const intervalRef  = useRef(null)
  const watchedRef   = useRef(0)

  // ── Load history on mount ─────────────────────────────────────────────────
  const fetchHistory = useCallback(() => {
    api.get('/youtube/history')
      .then(r => setHistory(r.data.history || []))
      .catch(() => {})
      .finally(() => setHistLoading(false))
  }, [])

  useEffect(() => { fetchHistory() }, [fetchHistory])

  // ── Build / rebuild player when videoId changes ───────────────────────────
  useEffect(() => {
    if (!videoId) return

    setSkillData(null)
    setStatus('Detecting…')
    watchedRef.current = 0
    clearInterval(intervalRef.current)

    loadYTApi(() => {
      // Destroy previous player
      if (playerRef.current) {
        try { playerRef.current.destroy() } catch {}
        playerRef.current = null
      }

      playerRef.current = new window.YT.Player('yt-embed', {
        videoId,
        playerVars: { rel: 0, modestbranding: 1, enablejsapi: 1 },
        events: {
          onReady(e) {
            const title = e.target.getVideoData()?.title
            if (title) fetchSkill(title)
          },
          onStateChange(e) {
            if (e.data === window.YT.PlayerState.PLAYING) {
              intervalRef.current = setInterval(() => {
                watchedRef.current += 30
                sendProgress(e.target)
              }, 30_000)
            } else if (
              e.data === window.YT.PlayerState.PAUSED ||
              e.data === window.YT.PlayerState.ENDED
            ) {
              clearInterval(intervalRef.current)
              if (watchedRef.current >= 10) sendProgress(e.target)
            }
          },
        },
      })
    })

    return () => {
      clearInterval(intervalRef.current)
      if (playerRef.current) {
        try { playerRef.current.destroy() } catch {}
        playerRef.current = null
      }
    }
  }, [videoId])   // eslint-disable-line react-hooks/exhaustive-deps

  // ── Skill detection ───────────────────────────────────────────────────────
  async function fetchSkill(title) {
    try {
      const { data } = await api.post('/youtube/match-skill', { video_title: title })
      setSkillData(data)
      if (!data.is_relevant || data.confidence < 0.6) setStatus('Not part of curriculum')
      else setStatus('')
    } catch {
      setStatus('Skill detection unavailable')
    }
  }

  // ── Progress tracking ─────────────────────────────────────────────────────
  async function sendProgress(player) {
    if (!skillData?.is_relevant) return
    try {
      const vd = player.getVideoData()
      const { data } = await api.post('/youtube/track', {
        video_id:        videoId,
        video_title:     vd.title,
        watched_seconds: Math.floor(player.getCurrentTime()),
        total_duration:  Math.floor(player.getDuration()),
      })
      if (data.progress_logged) {
        setStatus('✓ Progress saved')
        fetchHistory()
      }
    } catch {}
  }

  // ── Load button handler ───────────────────────────────────────────────────
  function handleLoad() {
    const id = extractId(urlInput)
    if (id) {
      setVideoId(prev => {
        // Force re-mount if same video
        if (prev === id) {
          setVideoId(null)
          setTimeout(() => setVideoId(id), 50)
          return null
        }
        return id
      })
    } else {
      setStatus('Invalid YouTube URL or video ID')
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6">
      <div className="max-w-3xl mx-auto space-y-6">

        {/* Header */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-red-600/20 flex items-center justify-center">
            <Youtube size={20} className="text-red-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">YouTube Learning Tracker</h1>
            <p className="text-xs text-slate-400">Watch a video — Claude AI detects the skill and logs your progress</p>
          </div>
        </div>

        {/* URL input */}
        <div className="flex gap-2">
          <input
            className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-violet-500 transition-colors"
            placeholder="Paste YouTube URL or video ID…"
            value={urlInput}
            onChange={e => setUrlInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleLoad()}
          />
          <button
            onClick={handleLoad}
            className="px-5 py-2.5 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-sm font-medium transition-colors"
          >
            Load
          </button>
        </div>

        {/* Player */}
        {videoId && (
          <div className="rounded-xl overflow-hidden border border-slate-800 bg-black">
            <div className="relative" style={{ paddingTop: '56.25%' }}>
              <div id="yt-embed" style={{ position: 'absolute', inset: 0 }} />
            </div>
            <SkillBar skillData={skillData} status={status} />
          </div>
        )}

        {/* Watch history */}
        <div>
          <h2 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
            <Clock size={15} className="text-slate-500" />
            Watch History
          </h2>

          {histLoading ? (
            <p className="text-xs text-slate-500 animate-pulse">Loading…</p>
          ) : history.length === 0 ? (
            <div className="text-sm text-slate-500 bg-slate-900 rounded-lg p-4 border border-slate-800">
              No videos tracked yet. Paste a YouTube link above to start.
            </div>
          ) : (
            <div className="space-y-2">
              {history.map(t => (
                <HistoryRow key={t.track_id} track={t} onReload={id => { setUrlInput(id); setVideoId(id) }} />
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
