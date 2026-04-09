(function () {
  'use strict';

  var API_BASE = window.ECHOFY_API_BASE || '';
  var fetchOpts = { credentials: 'include' };

  // Get user ID from query string: /user?id=123
  var params = new URLSearchParams(window.location.search);
  var userId = params.get('id');

  var usernameEl = document.getElementById('user-username');
  var metaEl = document.getElementById('user-meta');
  var avatarEl = document.getElementById('user-avatar');
  var detailsEl = document.getElementById('user-details');
  var errorEl = document.getElementById('user-error');

  if (!userId) {
    usernameEl.textContent = 'User not found';
    errorEl.textContent = 'No user specified.';
    errorEl.hidden = false;
    return;
  }

  fetch(API_BASE + '/api/users/' + userId + '/profile', fetchOpts)
    .then(function (res) {
      if (res.status === 401) {
        window.location.href = 'login';
        return null;
      }
      return res.json();
    })
    .then(function (data) {
      if (!data || !data.ok) {
        usernameEl.textContent = 'Profile unavailable';
        errorEl.textContent = (data && data.errors) ? data.errors.join(' ') : 'Could not load profile.';
        errorEl.hidden = false;
        return;
      }

      var p = data.profile;

      // Avatar
      avatarEl.textContent = '';
      avatarEl.innerHTML = '';
      if (p.profile_image_url) {
        var img = document.createElement('img');
        img.src = p.profile_image_url;
        img.alt = p.username + ' profile photo';
        img.className = 'profile-avatar-img';
        avatarEl.appendChild(img);
      } else {
        avatarEl.textContent = p.username.substring(0, 2).toUpperCase();
      }

      // Username
      usernameEl.textContent = p.username;
      document.title = p.username + ' — Echofy';

      // Bio
      if (p.bio) {
        document.getElementById('user-bio').textContent = p.bio;
        document.getElementById('field-bio').hidden = false;
      }

      // Favorite genre
      if (p.favorite_genre) {
        document.getElementById('user-genre').textContent = p.favorite_genre;
        document.getElementById('field-genre').hidden = false;
      }

      detailsEl.hidden = false;
    })
    .catch(function () {
      usernameEl.textContent = 'Error';
      errorEl.textContent = 'Network error loading profile.';
      errorEl.hidden = false;
    });
})();
