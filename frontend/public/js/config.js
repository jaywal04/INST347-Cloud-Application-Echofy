/**
 * Shared API configuration.
 *
 * Local dev  → http://127.0.0.1:5001
 * Production → fetched from the backend's /api/config endpoint,
 *              or set ECHOFY_BACKEND_URL in .env on the server.
 */
(function () {
  'use strict';

  var host = window.location.hostname;
  var isLocal = host === 'localhost' || host === '127.0.0.1';

  function routeHref(route) {
    var value = String(route || '').trim();
    if (!value || value === '#') return value;
    if (/^(https?:)?\/\//.test(value) || value.indexOf('#') === 0) return value;
    if (value === '/') return isLocal ? '/index.html' : '/';
    if (!isLocal) return value;
    if (value.slice(-5) === '.html') return value;
    if (value.indexOf('/') !== -1) return value;
    return value + '.html';
  }

  window.ECHOFY_ROUTE = routeHref;

  if (isLocal) {
    window.ECHOFY_API_BASE = 'http://127.0.0.1:5001';
    document.addEventListener('DOMContentLoaded', function () {
      document.querySelectorAll('a[href]').forEach(function (anchor) {
        var href = anchor.getAttribute('href');
        anchor.setAttribute('href', routeHref(href));
      });
    });
    return;
  }

  // Production — point to the deployed backend.
  window.ECHOFY_API_BASE = 'https://echofy-backend-c7b8a0are7abgxhn.canadacentral-01.azurewebsites.net';
})();
