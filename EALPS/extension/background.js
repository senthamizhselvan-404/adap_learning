// background.js — service worker
// Receives messages from content_script, POSTs to EALPS backend.

'use strict';

// TODO: replace with env var or options page setting before production
const API_BASE = 'http://localhost:5000';

async function getUserId() {
  return new Promise(resolve => {
    chrome.storage.local.get('learner_userId', r => resolve(r.learner_userId || null));
  });
}

async function postTrack(payload) {
  const userId = await getUserId();
  if (!userId || !payload.videoId) return;

  // TODO: backend endpoint — POST /api/extension/track
  try {
    const res = await fetch(`${API_BASE}/api/extension/track`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ ...payload, userId }),
    });
    if (!res.ok) return;
    const data = await res.json();
    // Cache latest skill-match result so popup can read without an extra request
    chrome.storage.local.set({ lastTrackResponse: data });
  } catch {
    // Fail silently — user may be offline or backend not running
  }
}

async function postComplete(payload) {
  const userId = await getUserId();
  if (!userId || !payload.videoId) return;

  // TODO: backend endpoint — POST /api/extension/complete
  try {
    await fetch(`${API_BASE}/api/extension/complete`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ ...payload, userId, completed: true }),
    });
  } catch {
    // Fail silently
  }
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === 'TRACK_PROGRESS') {
    postTrack(msg.payload);
    sendResponse({ ok: true });
  }
  if (msg.type === 'MARK_COMPLETE') {
    postComplete(msg.payload);
    sendResponse({ ok: true });
  }
  return true; // keep channel open for async responses
});
