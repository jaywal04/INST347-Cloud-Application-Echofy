(function () {
  'use strict';

  var API_BASE = window.ECHOFY_API_BASE || '';

  function reveal() {
    var el = document.getElementById('nav-auth');
    if (el) el.classList.add('ready');
  }

  fetch(API_BASE + '/api/auth/me', { credentials: 'include' })
    .then(function (res) { return res.json(); })
    .then(function (data) {
      var navAuth = document.getElementById('nav-auth');
      if (!navAuth) return;
      if (!data.authenticated || !data.user) {
        var signIn = document.createElement('a');
        signIn.href = 'login';
        signIn.className = 'nav-cta';
        signIn.textContent = 'Sign In';
        navAuth.appendChild(signIn);
        reveal();
        return;
      }
      if (data.authenticated && data.user) {
        var u = data.user;
        var initials = u.username.substring(0, 2).toUpperCase();

        var bellLink = document.createElement('a');
        bellLink.href = 'notifications';
        bellLink.className = 'nav-notif-link';
        bellLink.title = 'Notifications';
        bellLink.innerHTML =
          '<svg class="nav-notif-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
            '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>' +
            '<path d="M13.73 21a2 2 0 0 1-3.46 0"/>' +
          '</svg>';

        var profileLink = document.createElement('a');
        profileLink.href = 'profile';
        profileLink.className = 'nav-profile-link';
        if (u.profile_image_url) {
          var img = document.createElement('img');
          img.className = 'nav-avatar-img';
          img.alt = '';
          img.src = u.profile_image_url;
          profileLink.appendChild(img);
        } else {
          var div = document.createElement('div');
          div.className = 'nav-avatar';
          div.textContent = initials;
          profileLink.appendChild(div);
        }

        navAuth.innerHTML = '';
        navAuth.appendChild(bellLink);
        navAuth.appendChild(profileLink);
        reveal();

        fetch(API_BASE + '/api/notifications/count', { credentials: 'include' })
          .then(function (res) { return res.json(); })
          .then(function (d) {
            if (d.ok && d.count > 0) {
              var badge = document.createElement('span');
              badge.className = 'nav-notif-badge';
              badge.textContent = d.count > 99 ? '99+' : d.count;
              bellLink.appendChild(badge);
            }
          })
          .catch(function () {});
      } else {
        reveal();
      }
    })
    .catch(function () {
      reveal();
    });
})();
