(function () {
  'use strict';

  var API_BASE = window.ECHOFY_API_BASE || '';

  var nav = document.createElement('nav');

  var logo = document.createElement('a');
  logo.className = 'logo';
  logo.href = '/';
  logo.innerHTML = 'Echo<span>fy</span>';

  var ul = document.createElement('ul');
  ul.className = 'nav-links';

  var authDiv = document.createElement('div');
  authDiv.id = 'nav-auth';

  nav.appendChild(logo);
  nav.appendChild(ul);
  nav.appendChild(authDiv);

  var placeholder = document.getElementById('navbar');
  if (placeholder) {
    placeholder.replaceWith(nav);
  }

  function reveal() {
    nav.classList.add('ready');
  }

  function appendNavLinks(links) {
    ul.innerHTML = '';
    links.forEach(function (link) {
      var li = document.createElement('li');
      var a = document.createElement('a');
      a.href = link.href;
      a.textContent = link.text;
      if (link.active) {
        a.className = 'is-active';
      }
      li.appendChild(a);
      ul.appendChild(li);
    });
  }

  function buildMainNav(username) {
    var base = '/' + encodeURIComponent(username);
    var pathParts = window.location.pathname.split('/').filter(Boolean);
    var activeSeg =
      pathParts.length >= 2 && pathParts[0] === username ? pathParts[1] : '';

    appendNavLinks([
      {
        href: base + '/discovery',
        text: 'Discover',
        active:
          activeSeg === 'discovery' ||
          activeSeg === 'dashboard' ||
          activeSeg === 'discover',
      },
      { href: base + '/friends', text: 'Friends', active: activeSeg === 'friends' },
      { href: '#', text: 'Your Echo', active: false },
    ]);
  }

  function buildPublicNav() {
    var pathParts = window.location.pathname.split('/').filter(Boolean);
    var p0 = (pathParts[0] || '').toLowerCase();
    var activeDiscover =
      pathParts.length === 1 &&
      (p0 === 'discover' || p0 === 'discovery' || p0 === 'dashboard');
    var activeFriends = pathParts.length === 1 && p0 === 'friends';
    appendNavLinks([
      { href: '/discover', text: 'Discover', active: activeDiscover },
      { href: '/friends', text: 'Friends', active: activeFriends },
      { href: '#', text: 'Your Echo', active: false },
    ]);
  }

  buildPublicNav();

  fetch(API_BASE + '/api/auth/me', { credentials: 'include' })
    .then(function (res) {
      return res.json();
    })
    .then(function (data) {
      if (!data.authenticated || !data.user) {
        buildPublicNav();
        var signIn = document.createElement('a');
        signIn.href = '/login';
        signIn.className = 'nav-cta';
        signIn.textContent = 'Sign In';
        authDiv.appendChild(signIn);
        reveal();
        return;
      }

      var u = data.user;
      var initials = u.username.substring(0, 2).toUpperCase();
      var base = '/' + encodeURIComponent(u.username);

      buildMainNav(u.username);

      var bellLink = document.createElement('a');
      bellLink.href = base + '/notifications';
      bellLink.className = 'nav-notif-link';
      bellLink.title = 'Notifications';
      bellLink.innerHTML =
        '<svg class="nav-notif-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
          '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>' +
          '<path d="M13.73 21a2 2 0 0 1-3.46 0"/>' +
        '</svg>';

      var profileLink = document.createElement('a');
      profileLink.href = base + '/profile';
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

      var pathParts = window.location.pathname.split('/').filter(Boolean);
      var activeSeg =
        pathParts.length >= 2 && pathParts[0] === u.username ? pathParts[1] : '';
      if (activeSeg === 'notifications') {
        bellLink.className += ' is-active';
      }
      if (activeSeg === 'profile') {
        profileLink.className += ' is-active';
      }

      authDiv.innerHTML = '';
      authDiv.appendChild(bellLink);
      authDiv.appendChild(profileLink);

      var heroSignup = document.getElementById('hero-signup-link');
      if (heroSignup) {
        heroSignup.remove();
      }

      var heroTitle = document.getElementById('hero-title');
      if (heroTitle && u.username) {
        heroTitle.innerHTML = '';
        heroTitle.appendChild(document.createTextNode('Welcome back, '));
        var nameEm = document.createElement('em');
        nameEm.textContent = u.username;
        heroTitle.appendChild(nameEm);
      }

      reveal();

      fetch(API_BASE + '/api/notifications/count', { credentials: 'include' })
        .then(function (res) {
          return res.json();
        })
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
