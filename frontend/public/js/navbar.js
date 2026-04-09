(function () {
  'use strict';

  // --- Config (inline so navbar is self-contained) ---
  var host = window.location.hostname;
  var API_BASE;
  if (host === 'localhost' || host === '127.0.0.1') {
    API_BASE = 'http://127.0.0.1:5001';
  } else {
    API_BASE = 'https://echofy-backend-c7b8a0are7abgxhn.canadacentral-01.azurewebsites.net';
  }
  // Expose for other page scripts that still read it
  if (!window.ECHOFY_API_BASE) window.ECHOFY_API_BASE = API_BASE;

  // --- Build nav structure ---
  var raw = window.location.pathname.split('/').pop().replace('.html', '') || '';
  var page = raw || '/';

  var links = [
    { href: 'discover', text: 'Discover' },
    { href: 'friends', text: 'Friends' },
    { href: '#', text: 'Your Echo' },
  ];

  var nav = document.createElement('nav');

  var logo = document.createElement('a');
  logo.className = 'logo';
  logo.href = '/';
  logo.innerHTML = 'Echo<span>fy</span>';

  var ul = document.createElement('ul');
  ul.className = 'nav-links';

  links.forEach(function (link) {
    var li = document.createElement('li');
    var a = document.createElement('a');
    a.href = link.href;
    a.textContent = link.text;
    if (page === link.href) {
      a.className = 'is-active';
    }
    li.appendChild(a);
    ul.appendChild(li);
  });

  var authDiv = document.createElement('div');
  authDiv.id = 'nav-auth';

  nav.appendChild(logo);
  nav.appendChild(ul);
  nav.appendChild(authDiv);

  var placeholder = document.getElementById('navbar');
  if (placeholder) {
    placeholder.replaceWith(nav);
  }

  // --- Auth state (replaces nav-auth.js) ---
  function reveal() {
    nav.classList.add('ready');
  }

  fetch(API_BASE + '/api/auth/me', { credentials: 'include' })
    .then(function (res) { return res.json(); })
    .then(function (data) {
      if (!data.authenticated || !data.user) {
        var signIn = document.createElement('a');
        signIn.href = 'login';
        signIn.className = 'nav-cta';
        signIn.textContent = 'Sign In';
        authDiv.appendChild(signIn);
        reveal();
        return;
      }

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

      authDiv.innerHTML = '';
      authDiv.appendChild(bellLink);
      authDiv.appendChild(profileLink);
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
    })
    .catch(function () {
      reveal();
    });
})();
