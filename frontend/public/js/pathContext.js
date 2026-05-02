(function () {
  'use strict';

  var STATIC_FIRST_SEGMENTS = { css: 1, js: 1, assets: 1, fonts: 1 };
  var APP_PAGES = {
    discovery: 1,
    dashboard: 1,
    discover: 1,
    review: 1,
    friends: 1,
    profile: 1,
    notifications: 1,
    user: 1,
  };

  window.ECHOFY_PATH_USERNAME = '';
  window.ECHOFY_USER_BASE = '';

  var stashed =
    typeof sessionStorage !== 'undefined' &&
    sessionStorage.getItem('echofy_prefixed_path');
  if (stashed) {
    try {
      var u = new URL(stashed, window.location.origin);
      if (
        /^\/[^/]+\/(discovery|dashboard|discover|review|friends|profile|notifications|user)(?:\/|$)/.test(
          u.pathname
        )
      ) {
        try {
          history.replaceState(null, '', stashed);
        } catch (e) {}
      }
    } catch (e2) {}
    try {
      sessionStorage.removeItem('echofy_prefixed_path');
    } catch (e3) {}
  }

  var parts = window.location.pathname.split('/').filter(Boolean);
  if (
    parts.length >= 2 &&
    !STATIC_FIRST_SEGMENTS[(parts[0] || '').toLowerCase()]
  ) {
    var page = (parts[1] || '').split('?')[0];
    if (APP_PAGES[page]) {
      window.ECHOFY_PATH_USERNAME = parts[0];
      window.ECHOFY_USER_BASE = '/' + parts[0];
    }
  }

  window.echofyUserPath = function (segment) {
    var seg = String(segment || '')
      .replace(/^\/+/, '')
      .replace(/\/+$/, '');
    var base = window.ECHOFY_USER_BASE || '';
    if (!base) {
      return '/' + seg;
    }
    return base + '/' + seg;
  };

  if (!window.ECHOFY_USER_BASE) {
    return;
  }

  fetch(
    (typeof window.echofyApiBaseUrl === 'function'
      ? window.echofyApiBaseUrl()
      : String(window.ECHOFY_API_BASE || '').trim().replace(/\/+$/, '')) + '/api/auth/me',
    { credentials: 'include' }
  )
    .then(function (res) {
      return res.json();
    })
    .then(function (data) {
      if (!data.authenticated || !data.user) {
        window.location.replace('/login');
        return;
      }
      if (data.user.username !== window.ECHOFY_PATH_USERNAME) {
        var rest = window.location.pathname.slice(
          window.ECHOFY_USER_BASE.length
        );
        var qs = window.location.search || '';
        window.location.replace(
          '/' + encodeURIComponent(data.user.username) + rest + qs
        );
      }
    })
    .catch(function () {
      window.location.replace('/login');
    });
})();
