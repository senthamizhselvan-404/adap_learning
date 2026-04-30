// content_script.js — runs on https://www.youtube.com/watch*
// Extracts video metadata and tracks watch time every 30 seconds.

(function () {
  'use strict';

  let trackingInterval = null;
  let lastReportedTime = 0;

  function getVideoId() {
    return new URLSearchParams(window.location.search).get('v') || '';
  }

  function getVideoTitle() {
    return document.title.replace(' - YouTube', '').trim();
  }

  function getChannelName() {
    const el = document.querySelector('#channel-name a, #channel-name yt-formatted-string');
    return el ? el.innerText.trim() : 'Unknown Channel';
  }

  function getVideoEl() {
    return document.querySelector('video.html5-main-video') || document.querySelector('video');
  }

  function buildPayload() {
    const vid = getVideoEl();
    return {
      videoId:        getVideoId(),
      videoTitle:     getVideoTitle(),
      channelName:    getChannelName(),
      videoDuration:  vid ? Math.floor(vid.duration)   : 0,
      currentTime:    vid ? Math.floor(vid.currentTime) : 0,
      watchedSeconds: vid ? Math.floor(vid.currentTime - lastReportedTime) : 0,
    };
  }

  function sendProgress() {
    const payload = buildPayload();
    if (!payload.videoId || payload.watchedSeconds <= 0) return;

    // TODO: background.js forwards this to POST /api/extension/track
    chrome.runtime.sendMessage({ type: 'TRACK_PROGRESS', payload });
    lastReportedTime = payload.currentTime;
  }

  function startTracking() {
    stopTracking();
    lastReportedTime = 0;
    trackingInterval = setInterval(sendProgress, 30_000);
  }

  function stopTracking() {
    if (trackingInterval) {
      clearInterval(trackingInterval);
      trackingInterval = null;
    }
  }

  // Re-start when YouTube navigates to a new video (SPA navigation)
  let lastVideoId = '';
  setInterval(() => {
    const id = getVideoId();
    if (id && id !== lastVideoId) {
      lastVideoId = id;
      startTracking();
    }
  }, 1500);

  // Listen for commands from popup.js
  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg.type === 'GET_VIDEO_INFO') {
      sendResponse({ ok: true, data: buildPayload() });
    }
    if (msg.type === 'MARK_COMPLETE') {
      // TODO: popup triggers final completion POST via background.js
      chrome.runtime.sendMessage({ type: 'MARK_COMPLETE', payload: buildPayload() });
      sendResponse({ ok: true });
    }
  });

  startTracking();
})();
