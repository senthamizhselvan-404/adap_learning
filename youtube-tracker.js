// ============================================================
//  youtube-tracker.js
//  Drop this ONE file into your project.
//  It handles everything on the frontend:
//    - Embeds a YouTube video player
//    - Tracks watch time automatically
//    - Calls your backend to identify the learning skill
//    - Shows the learner what skill they are studying
//
//  SETUP (one time):
//    1. Add this script tag to your HTML:
//       <script src="youtube-tracker.js"></script>
//
//    2. Add a container div where you want the player:
//       <div id="yt-tracker-widget" data-video-id="dQw4w9WgXcQ"></div>
//
//    3. Make sure your backend is running at the API_BASE_URL below.
//
//  THAT'S IT. Everything else is automatic.
// ============================================================


// ────────────────────────────────────────────────────────────
//  STEP 1 ── CONFIGURE (only thing you need to change)
// ────────────────────────────────────────────────────────────
const YT_TRACKER_CONFIG = {
  API_BASE_URL: "http://localhost:5000/api/v1/youtube", // Flask backend URL
  USER_ID: localStorage.getItem("userId") || "guest-user",  // logged-in user
  TRACK_INTERVAL_SECONDS: 30,   // how often to send watch data
  MIN_WATCH_SECONDS: 10,        // ignore if watched less than this
  CONFIDENCE_THRESHOLD: 0.6,    // min confidence to show skill badge
};


// ────────────────────────────────────────────────────────────
//  STYLES  (injected automatically — no separate CSS file)
// ────────────────────────────────────────────────────────────
(function injectStyles() {
  const style = document.createElement("style");
  style.textContent = `
    .yt-tracker-wrap {
      font-family: 'DM Sans', system-ui, sans-serif;
      border-radius: 12px;
      overflow: hidden;
      background: #0f0f0f;
      max-width: 800px;
    }
    .yt-player-box { position: relative; padding-top: 56.25%; background: #000; }
    .yt-player-box iframe { position: absolute; inset: 0; width: 100%; height: 100%; border: 0; }

    .yt-skill-bar {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 14px;
      background: #1a1a1a;
      border-top: 1px solid #2a2a2a;
      min-height: 44px;
    }
    .yt-skill-label {
      font-size: 11px;
      color: #666;
      white-space: nowrap;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }
    .yt-skill-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 3px 10px;
      background: #2d1f6e;
      border: 1px solid #4c35b5;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 500;
      color: #a78bfa;
      animation: yt-badge-in 0.3s ease;
    }
    .yt-skill-dot {
      width: 6px; height: 6px;
      border-radius: 50%;
      background: #7c3aed;
    }
    .yt-confidence {
      font-size: 11px;
      color: #555;
      margin-left: auto;
      white-space: nowrap;
    }
    .yt-conf-bar {
      display: inline-block;
      width: 60px; height: 4px;
      background: #2a2a2a;
      border-radius: 2px;
      vertical-align: middle;
      margin-right: 4px;
      overflow: hidden;
    }
    .yt-conf-fill {
      height: 100%;
      border-radius: 2px;
      background: #7c3aed;
      transition: width 0.5s ease;
    }
    .yt-status {
      font-size: 11px;
      color: #555;
      margin-left: auto;
    }
    .yt-logged { color: #22c55e !important; }
    @keyframes yt-badge-in {
      from { opacity: 0; transform: translateY(4px); }
      to   { opacity: 1; transform: translateY(0); }
    }
  `;
  document.head.appendChild(style);
})();


// ────────────────────────────────────────────────────────────
//  MAIN CLASS  YouTubeSkillTracker
// ────────────────────────────────────────────────────────────
class YouTubeSkillTracker {
  constructor(containerEl, videoId) {
    this.container = containerEl;
    this.videoId = videoId;
    this.player = null;
    this.trackInterval = null;
    this.lastTrackedAt = 0;
    this.skillData = null;
    this.sessionWatched = 0;

    this._buildUI();
    this._loadYouTubeAPI();
  }

  // ── 1. Build the player UI ──────────────────────────────
  _buildUI() {
    this.container.innerHTML = `
      <div class="yt-tracker-wrap">
        <div class="yt-player-box">
          <div id="yt-iframe-${this.videoId}"></div>
        </div>
        <div class="yt-skill-bar" id="yt-skill-bar-${this.videoId}">
          <span class="yt-skill-label">Skill</span>
          <span class="yt-status" id="yt-status-${this.videoId}">Detecting…</span>
        </div>
      </div>`;
  }

  // ── 2. Load YouTube IFrame API ──────────────────────────
  _loadYouTubeAPI() {
    if (window.YT && window.YT.Player) {
      this._initPlayer();
      return;
    }
    if (!document.getElementById("yt-api-script")) {
      const tag = document.createElement("script");
      tag.id = "yt-api-script";
      tag.src = "https://www.youtube.com/iframe_api";
      document.head.appendChild(tag);
    }
    // Queue init — YouTube API calls this globally once loaded
    const prev = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = () => {
      if (prev) prev();
      this._initPlayer();
    };
  }

  // ── 3. Initialize the player ────────────────────────────
  _initPlayer() {
    this.player = new YT.Player(`yt-iframe-${this.videoId}`, {
      videoId: this.videoId,
      playerVars: { rel: 0, modestbranding: 1 },
      events: {
        onReady: () => this._onPlayerReady(),
        onStateChange: (e) => this._onStateChange(e),
      },
    });
  }

  // ── 4. When player is ready — fetch skill immediately ───
  _onPlayerReady() {
    const title = this.player.getVideoData().title;
    if (title) this._matchSkill(title);
  }

  // ── 5. React to play / pause / end ─────────────────────
  _onStateChange(event) {
    const state = event.data;

    if (state === YT.PlayerState.PLAYING) {
      // Start tracking every N seconds
      this.trackInterval = setInterval(() => {
        this.sessionWatched += YT_TRACKER_CONFIG.TRACK_INTERVAL_SECONDS;
        this._sendProgress();
      }, YT_TRACKER_CONFIG.TRACK_INTERVAL_SECONDS * 1000);
    }

    if (state === YT.PlayerState.PAUSED || state === YT.PlayerState.ENDED) {
      clearInterval(this.trackInterval);
      // Send final progress on pause/end
      if (this.sessionWatched >= YT_TRACKER_CONFIG.MIN_WATCH_SECONDS) {
        this._sendProgress();
      }
    }
  }

  // ── 6. Match skill via your backend ────────────────────
  async _matchSkill(videoTitle) {
    try {
      const res = await fetch(`${YT_TRACKER_CONFIG.API_BASE_URL}/match-skill`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_title: videoTitle }),
      });
      const data = await res.json();
      this.skillData = data;
      this._updateSkillBar(data);
    } catch {
      this._setStatus("Could not detect skill");
    }
  }

  // ── 7. Send watch progress to your backend ──────────────
  async _sendProgress() {
    if (!this.skillData?.is_relevant) return;

    const vd = this.player.getVideoData();
    try {
      const res = await fetch(`${YT_TRACKER_CONFIG.API_BASE_URL}/track`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: YT_TRACKER_CONFIG.USER_ID,
          video_id: this.videoId,
          video_title: vd.title,
          watched_seconds: Math.floor(this.player.getCurrentTime()),
          total_duration: Math.floor(this.player.getDuration()),
        }),
      });
      const data = await res.json();
      if (data.progress_logged) {
        this._setStatus("✓ Progress saved", true);
      }
    } catch {
      // Silent fail — don't interrupt the learner
    }
  }

  // ── 8. Update the skill badge UI ───────────────────────
  _updateSkillBar(data) {
    const bar = document.getElementById(`yt-skill-bar-${this.videoId}`);
    if (!bar) return;

    if (!data.is_relevant || data.confidence < YT_TRACKER_CONFIG.CONFIDENCE_THRESHOLD) {
      this._setStatus("Not part of your curriculum");
      return;
    }

    const pct = Math.round(data.confidence * 100);
    bar.innerHTML = `
      <span class="yt-skill-label">Skill</span>
      <span class="yt-skill-badge">
        <span class="yt-skill-dot"></span>
        ${data.matched_skill}
      </span>
      <span class="yt-confidence">
        <span class="yt-conf-bar">
          <span class="yt-conf-fill" style="width:${pct}%"></span>
        </span>
        ${pct}% match
      </span>`;
  }

  _setStatus(msg, success = false) {
    const el = document.getElementById(`yt-status-${this.videoId}`);
    if (el) {
      el.textContent = msg;
      if (success) el.classList.add("yt-logged");
    }
  }
}


// ────────────────────────────────────────────────────────────
//  AUTO-INIT
//  Finds every <div data-video-id="..."> on the page
//  and turns it into a tracked player automatically.
// ────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-video-id]").forEach((el) => {
    const videoId = el.getAttribute("data-video-id");
    if (videoId) new YouTubeSkillTracker(el, videoId);
  });
});


// ────────────────────────────────────────────────────────────
//  MANUAL API  (use this if you want to init yourself)
//
//  const tracker = new YouTubeSkillTracker(
//    document.getElementById("my-div"),
//    "dQw4w9WgXcQ"
//  );
// ────────────────────────────────────────────────────────────
window.YouTubeSkillTracker = YouTubeSkillTracker;
