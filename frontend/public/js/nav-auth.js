(function () {
  'use strict';

  var API_BASE = window.ECHOFY_API_BASE || '';

  fetch(API_BASE + '/api/auth/me', { credentials: 'include' })
    .then(function (res) { return res.json(); })
    .then(function (data) {
      var navAuth = document.getElementById('nav-auth');
      if (!navAuth) return;
      if (data.authenticated && data.user) {
        var u = data.user;
        var initials = u.username.substring(0, 2).toUpperCase();
        var link = document.createElement('a');
        link.href = 'profile.html';
        link.className = 'nav-profile-link';
        if (u.profile_image_url) {
          var img = document.createElement('img');
          img.className = 'nav-avatar-img';
          img.alt = '';
          img.src = u.profile_image_url;
          link.appendChild(img);
        } else {
          var div = document.createElement('div');
          div.className = 'nav-avatar';
          div.textContent = initials;
          link.appendChild(div);
        }
        navAuth.innerHTML = '';
        navAuth.appendChild(link);
      }
    })
    .catch(function () {});
})();
