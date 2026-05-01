(function () {
  'use strict';

  var host = window.location.hostname;
  var API_BASE;
  if (host === 'localhost') {
    API_BASE = 'http://localhost:5001';
  } else if (host === '127.0.0.1') {
    API_BASE = 'http://127.0.0.1:5001';
  } else {
    API_BASE = 'https://echofy-backend-c7b8a0are7abgxhn.canadacentral-01.azurewebsites.net';
  }
  if (!window.ECHOFY_API_BASE) {
    window.ECHOFY_API_BASE = API_BASE;
  }

  var STATIC_FIRST_SEGMENTS = { css: 1, js: 1, assets: 1, fonts: 1 };
  var APP_PAGES = {
    dashboard: 1,
    discover: 1,
    friends: 1,
    profile: 1,
    notifications: 1,
    user: 1,
  };

  window.ECHOFY_PATH_USERNAME = '';
  window.ECHOFY_USER_BASE = '';

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

  fetch(window.ECHOFY_API_BASE + '/api/auth/me', { credentials: 'include' })
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
