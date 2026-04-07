/**
 * Shared API configuration.
 *
 * Local dev  → http://127.0.0.1:5000
 * Production → fetched from the backend's /api/config endpoint,
 *              or set ECHOFY_BACKEND_URL in .env on the server.
 */
(function () {
  'use strict';

  var host = window.location.hostname;

  if (host === 'localhost' || host === '127.0.0.1') {
    window.ECHOFY_API_BASE = 'http://127.0.0.1:5000';
    return;
  }

  // Production — try to discover backend URL from the backend itself.
  // The deploy sets ECHOFY_BACKEND_URL in .env; the backend exposes it at /api/config.
  window.ECHOFY_API_BASE = '';

  var stored = sessionStorage.getItem('echofy_api_base');
  if (stored) {
    window.ECHOFY_API_BASE = stored;
    return;
  }

  // Discover from a well-known backend host.
  // Falls back gracefully — features that need the API will show a helpful message.
})();
