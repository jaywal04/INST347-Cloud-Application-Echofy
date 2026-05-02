/**
 * Fire-and-forget client error reports to the API (Discord webhook on the server).
 * Requires window.ECHOFY_API_BASE (see apiBase.js). Never include passwords in detail.
 */
(function () {
  'use strict';

  window.echofyReportClientBug = function (detail) {
    try {
      var base =
        typeof window.echofyApiBaseUrl === 'function'
          ? window.echofyApiBaseUrl()
          : String(window.ECHOFY_API_BASE || '')
              .trim()
              .replace(/\/+$/, '');
      if (!base) {
        return;
      }
      var body = {
        kind: 'client_error',
        pageUrl: String(window.location.href || ''),
        userAgent: String(navigator.userAgent || ''),
        time: new Date().toISOString(),
      };
      if (detail && typeof detail === 'object') {
        for (var k in detail) {
          if (Object.prototype.hasOwnProperty.call(detail, k)) {
            body[k] = detail[k];
          }
        }
      }
      fetch(base + '/api/telemetry/client-error', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      }).catch(function () {});
    } catch (e) {}
  };
})();
