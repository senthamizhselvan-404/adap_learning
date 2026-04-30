// popup.js — runs inside popup.html
'use strict';

const API_BASE = 'http://localhost:5000';

const $ = id => document.getElementById(id);

// ── Helpers ──────────────────────────────────────────────────────────────────

function show(id)  { $(id).classList.remove('hidden'); }
function hide(id)  { $(id).classList.add('hidden'); }
function setText(id, v) { $(id).textContent = v; }

function setProgress(pct) {
  const clamped = Math.min(100, Math.max(0, pct));
  $('progress-fill').style.width = `${clamped}%`;
  setText('progress-pct', `${Math.round(clamped)}%`);
}

// ── User ID persistence ───────────────────────────────────────────────────────

chrome.storage.local.get('learner_userId', r => {
  if (r.learner_userId) $('user-id-input').value = r.learner_userId;
});

$('btn-save-id').addEventListener('click', () => {
  const id = $('user-id-input').value.trim();
  if (!id) return;
  chrome.storage.local.set({ learner_userId: id }, () => {
    $('btn-save-id').textContent = 'Saved ✓';
    setTimeout(() => { $('btn-save-id').textContent = 'Save'; }, 1500);
  });
});

// ── Fetch skill match from backend ───────────────────────────────────────────

async function loadSkillMatch(videoId) {
  // TODO: backend endpoint — GET /api/extension/skill-match?videoId=X
  try {
    const res  = await fetch(`${API_BASE}/api/extension/skill-match?videoId=${videoId}`);
    if (!res.ok) throw new Error('no match');
    const data = await res.json();

    setText('skill-name', data.skillName  || 'Unknown Skill');
    setProgress(data.progressPct          || 0);
    setText('time-left', data.minutesLeft != null
      ? `${data.minutesLeft} min left` : '— min left');
    setText('status-badge', 'Tracking');
    $('status-badge').className = 'badge badge-active';
  } catch {
    setText('skill-name', 'No skill mapped');
    setText('status-badge', 'No match');
  }
}

// ── Query active tab and bootstrap UI ────────────────────────────────────────

async function init() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  const isYouTubeVideo =
    tab && tab.url && tab.url.includes('youtube.com/watch');

  if (!isYouTubeVideo) {
    setText('status-badge', 'Not on video');
    show('no-video');
    return;
  }

  // Ask content script for live video data
  let videoData = null;
  try {
    const resp = await chrome.tabs.sendMessage(tab.id, { type: 'GET_VIDEO_INFO' });
    if (resp?.ok) videoData = resp.data;
  } catch {
    // Content script not yet injected — tab may still be loading
  }

  show('video-card');
  if (videoData) {
    setText('video-title',   videoData.videoTitle   || 'Unknown Title');
    setText('channel-name',  videoData.channelName  || 'Unknown Channel');
    await loadSkillMatch(videoData.videoId);
  }
}

// ── Button handlers ───────────────────────────────────────────────────────────

$('btn-complete').addEventListener('click', async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) return;
  // TODO: triggers MARK_COMPLETE in content_script → background → backend
  await chrome.tabs.sendMessage(tab.id, { type: 'MARK_COMPLETE' });
  $('btn-complete').textContent = 'Completed ✓';
  $('btn-complete').disabled = true;
  setProgress(100);
});

$('btn-skip').addEventListener('click', () => window.close());

// ── Run ───────────────────────────────────────────────────────────────────────

init();
