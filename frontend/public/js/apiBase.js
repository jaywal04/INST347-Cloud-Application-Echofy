/**
 * Sets window.ECHOFY_API_BASE before any other app scripts run.
 *
 * Local dev: same host as the page on port 5001.
 * Production: reads /echofy-config.json (same origin). CI writes that file from secrets.
 */
(function () {
  'use strict';

  var h = window.location.hostname;

  if (h === 'localhost') {
    window.ECHOFY_API_BASE = 'http://localhost:5001';
    return;
  }
  if (h === '127.0.0.1') {
    window.ECHOFY_API_BASE = 'http://127.0.0.1:5001';
    return;
  }

  try {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/echofy-config.json', false);
    xhr.send(null);
    if (xhr.status === 200) {
      var j = JSON.parse(xhr.responseText);
      if (j && typeof j.apiBase === 'string' && j.apiBase.trim()) {
        window.ECHOFY_API_BASE = j.apiBase.replace(/\/+$/, '');
        return;
      }
    }
  } catch (e) {}

  console.error(
    '[echofy] Missing /echofy-config.json with { "apiBase": "https://your-api..." }. See echofy-config.example.json.'
  );
  window.ECHOFY_API_BASE = '';
})();
