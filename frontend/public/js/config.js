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

  // Production — point to the deployed backend.
  window.ECHOFY_API_BASE = 'https://echofy-backend.azurewebsites.net';
})();
