/**
 * Shared API configuration.
 *
 * Local dev  → same hostname as this page (localhost or 127.0.0.1) on port 5001
 * Production → deployed backend URL below
 */
(function () {
  'use strict';

  var host = window.location.hostname;

  if (host === 'localhost') {
    window.ECHOFY_API_BASE = 'http://localhost:5001';
    return;
  }
  if (host === '127.0.0.1') {
    window.ECHOFY_API_BASE = 'http://127.0.0.1:5001';
    return;
  }

  // Production — point to the deployed backend.
  window.ECHOFY_API_BASE = 'https://echofy-backend-c7b8a0are7abgxhn.canadacentral-01.azurewebsites.net';
})();
