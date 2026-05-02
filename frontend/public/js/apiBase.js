/**
 * Sets window.ECHOFY_API_BASE and window.echofyApiBaseUrl() for all app scripts.
 *
 * Local dev: loopback and common static-server ports → API on :5001.
 * Production: reads /echofy-config.json (same origin). CI writes that file from secrets.
 */
(function () {
  'use strict';

  var h = String(window.location.hostname || '').trim().toLowerCase();
  var port = String(window.location.port || '');
  var proto = window.location.protocol || 'http:';

  function devFallbackApiBase() {
    if (h === '127.0.0.1') {
      return 'http://127.0.0.1:5001';
    }
    if (h === '::1') {
      return 'http://[::1]:5001';
    }
    if (!h || h === 'localhost') {
      return 'http://localhost:5001';
    }
    // e.g. http://192.168.x.x:3001 — same host, API on 5001
    if (
      proto === 'http:' &&
      (port === '3001' || port === '3000' || port === '8080') &&
      /^(\d{1,3}\.){3}\d{1,3}$/.test(h)
    ) {
      return 'http://' + h + ':5001';
    }
    return '';
  }

  function loadFromConfigJson() {
    try {
      var xhr = new XMLHttpRequest();
      xhr.open('GET', '/echofy-config.json', false);
      xhr.send(null);
      if (xhr.status === 200) {
        var j = JSON.parse(xhr.responseText);
        if (j && typeof j.apiBase === 'string' && j.apiBase.trim()) {
          return j.apiBase.replace(/\/+$/, '');
        }
      }
    } catch (e) {}
    return '';
  }

  if (h === 'localhost' || h === '') {
    window.ECHOFY_API_BASE = 'http://localhost:5001';
  } else if (h === '127.0.0.1') {
    window.ECHOFY_API_BASE = 'http://127.0.0.1:5001';
  } else if (h === '::1') {
    window.ECHOFY_API_BASE = 'http://[::1]:5001';
  } else {
    var fromJson = loadFromConfigJson();
    if (fromJson) {
      window.ECHOFY_API_BASE = fromJson;
    } else {
      var fb = devFallbackApiBase();
      window.ECHOFY_API_BASE = fb || '';
      if (!window.ECHOFY_API_BASE) {
        console.error(
          '[echofy] Missing /echofy-config.json with { "apiBase": "https://your-api..." }. See echofy-config.example.json.'
        );
      }
    }
  }

  /**
   * Always use this for API URLs (resolves after apiBase runs; includes dev fallbacks).
   */
  window.echofyApiBaseUrl = function () {
    var v = String(window.ECHOFY_API_BASE || '')
      .trim()
      .replace(/\/+$/, '');
    if (v) {
      return v;
    }
    return devFallbackApiBase();
  };
})();
