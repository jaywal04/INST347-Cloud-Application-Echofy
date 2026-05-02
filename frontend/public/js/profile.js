(function () {
  'use strict';

  var API_BASE = window.ECHOFY_API_BASE || '';
  var fetchOpts = { credentials: 'include', headers: { 'Content-Type': 'application/json' } };
  var MSG_NET =
    'Something went wrong. The team has been notified. Please try again shortly.';

  function reportProfile(scope, err, extra) {
    if (window.echofyReportClientBug) {
      window.echofyReportClientBug(
        Object.assign(
          {
            scope: scope,
            apiBasePresent: !!API_BASE,
            errorMessage: err && err.message ? String(err.message) : 'request_failed',
          },
          extra || {}
        )
      );
    }
  }

  // --- Tab switching ---
  var tabs = document.querySelectorAll('.profile-tab');
  var panels = document.querySelectorAll('.profile-tab-content');

  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      tabs.forEach(function (t) { t.classList.remove('active'); });
      panels.forEach(function (p) { p.classList.remove('active'); });
      tab.classList.add('active');
      document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
    });
  });

  function setLargeAvatar(el, username, imageUrl) {
    if (!el) return;
    el.textContent = '';
    el.innerHTML = '';
    if (imageUrl) {
      var img = document.createElement('img');
      img.src = imageUrl;
      img.alt = username + ' profile photo';
      img.className = 'profile-avatar-img';
      el.appendChild(img);
    } else {
      el.textContent = username.substring(0, 2).toUpperCase();
    }
  }

  // --- Load profile ---
  function loadProfile() {
    fetch(API_BASE + '/api/auth/profile', Object.assign({}, fetchOpts, { method: 'GET' }))
      .then(function (res) {
        if (res.status === 401) {
          window.location.href = '/login';
          return null;
        }
        return res.json();
      })
      .then(function (data) {
        if (!data || !data.ok) return;
        var p = data.profile;

        // Header
        setLargeAvatar(document.getElementById('profile-avatar'), p.username, p.profile_image_url);
        document.getElementById('profile-username').textContent = p.username;

        var removeBtn = document.getElementById('btn-remove-photo');
        if (removeBtn) removeBtn.disabled = !p.profile_image_url;

        var meta = 'Member since ' + new Date(p.created_at).toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
        if (p.location) meta += '  ·  ' + p.location;
        document.getElementById('profile-meta').textContent = meta;

        // Profile form
        document.getElementById('prof-username').value = p.username;
        document.getElementById('prof-email').value = p.email;
        document.getElementById('prof-age').value = p.age || '';
        document.getElementById('prof-sex').value = p.sex || '';
        document.getElementById('prof-location').value = p.location || '';
        document.getElementById('prof-genre').value = p.favorite_genre || '';
        document.getElementById('prof-bio').value = p.bio || '';

        // Privacy
        document.getElementById('priv-public').checked = p.profile_public;
        document.getElementById('priv-history').checked = p.show_listening_history;
        document.getElementById('priv-reviews').checked = p.show_reviews;
        document.getElementById('priv-bio').checked = p.show_bio !== false;
        document.getElementById('priv-genre').checked = p.show_genre !== false;
      })
      .catch(function (err) {
        reportProfile('profile.load', err, { endpoint: '/api/auth/profile' });
        document.getElementById('profile-username').textContent = 'Error loading profile';
      });
  }

  loadProfile();

  // --- Helper: show message ---
  function showMsg(el, text, isError) {
    el.hidden = false;
    el.textContent = text;
    el.className = 'profile-msg ' + (isError ? 'msg-error' : 'msg-success');
    setTimeout(function () { el.hidden = true; }, 3000);
  }

  // --- Save profile ---
  document.getElementById('profile-form').addEventListener('submit', function (e) {
    e.preventDefault();
    var btn = document.getElementById('btn-save-profile');
    btn.disabled = true;
    btn.textContent = 'Saving...';

    var body = {
      age: document.getElementById('prof-age').value ? parseInt(document.getElementById('prof-age').value) : null,
      sex: document.getElementById('prof-sex').value,
      bio: document.getElementById('prof-bio').value,
      location: document.getElementById('prof-location').value,
      favorite_genre: document.getElementById('prof-genre').value,
    };

    fetch(API_BASE + '/api/auth/profile', Object.assign({}, fetchOpts, {
      method: 'PUT',
      body: JSON.stringify(body),
    }))
      .then(function (res) { return res.json(); })
      .then(function (data) {
        var msgEl = document.getElementById('profile-msg');
        if (data.ok) {
          showMsg(msgEl, 'Profile updated successfully.', false);
          loadProfile();
        } else {
          showMsg(msgEl, (data.errors || ['Failed to save.']).join(' '), true);
        }
      })
      .catch(function (err) {
        reportProfile('profile.save', err, { endpoint: '/api/auth/profile' });
        showMsg(document.getElementById('profile-msg'), MSG_NET, true);
      })
      .finally(function () {
        btn.disabled = false;
        btn.textContent = 'Save Changes';
      });
  });

  // --- Profile photo upload / remove ---
  document.getElementById('btn-upload-photo').addEventListener('click', function () {
    var input = document.getElementById('prof-photo-file');
    var msgEl = document.getElementById('profile-msg');
    if (!input.files || !input.files[0]) {
      showMsg(msgEl, 'Choose an image file first.', true);
      return;
    }
    var btn = document.getElementById('btn-upload-photo');
    btn.disabled = true;
    btn.textContent = 'Uploading...';
    var fd = new FormData();
    fd.append('file', input.files[0]);
    fetch(API_BASE + '/api/auth/profile/photo', { method: 'POST', credentials: 'include', body: fd })
      .then(function (res) { return res.json().then(function (data) { return { res: res, data: data }; }); })
      .then(function (x) {
        if (x.data.ok) {
          showMsg(msgEl, 'Photo updated.', false);
          input.value = '';
          loadProfile();
        } else {
          showMsg(msgEl, (x.data.errors || ['Upload failed.']).join(' '), true);
        }
      })
      .catch(function (err) {
        reportProfile('profile.photo_upload', err, { endpoint: '/api/auth/profile/photo' });
        showMsg(msgEl, MSG_NET, true);
      })
      .finally(function () {
        btn.disabled = false;
        btn.textContent = 'Upload photo';
      });
  });

  document.getElementById('btn-remove-photo').addEventListener('click', function () {
    var msgEl = document.getElementById('profile-msg');
    var btn = document.getElementById('btn-remove-photo');
    btn.disabled = true;
    fetch(API_BASE + '/api/auth/profile/photo', { method: 'DELETE', credentials: 'include' })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (data.ok) {
          showMsg(msgEl, 'Photo removed.', false);
          loadProfile();
        } else {
          showMsg(msgEl, (data.errors || ['Could not remove photo.']).join(' '), true);
        }
      })
      .catch(function (err) {
        reportProfile('profile.photo_remove', err, { endpoint: '/api/auth/profile/photo' });
        showMsg(msgEl, MSG_NET, true);
      })
      .finally(function () {
        btn.disabled = false;
      });
  });

  // --- Save privacy ---
  document.getElementById('privacy-form').addEventListener('submit', function (e) {
    e.preventDefault();
    var btn = document.getElementById('btn-save-privacy');
    btn.disabled = true;
    btn.textContent = 'Saving...';

    var body = {
      profile_public: document.getElementById('priv-public').checked,
      show_listening_history: document.getElementById('priv-history').checked,
      show_reviews: document.getElementById('priv-reviews').checked,
      show_bio: document.getElementById('priv-bio').checked,
      show_genre: document.getElementById('priv-genre').checked,
    };

    fetch(API_BASE + '/api/auth/privacy', Object.assign({}, fetchOpts, {
      method: 'PUT',
      body: JSON.stringify(body),
    }))
      .then(function (res) { return res.json(); })
      .then(function (data) {
        var msgEl = document.getElementById('privacy-msg');
        if (data.ok) {
          showMsg(msgEl, 'Privacy settings saved.', false);
        } else {
          showMsg(msgEl, (data.errors || ['Failed to save.']).join(' '), true);
        }
      })
      .catch(function (err) {
        reportProfile('profile.privacy_save', err, { endpoint: '/api/auth/privacy' });
        showMsg(document.getElementById('privacy-msg'), MSG_NET, true);
      })
      .finally(function () {
        btn.disabled = false;
        btn.textContent = 'Save Privacy Settings';
      });
  });

  // --- Sign out ---
  document.getElementById('btn-signout').addEventListener('click', function () {
    var btn = document.getElementById('btn-signout');
    btn.disabled = true;
    btn.textContent = 'Signing out...';
    fetch(API_BASE + '/api/auth/logout', Object.assign({}, fetchOpts, { method: 'POST' }))
      .then(function () { window.location.href = '/'; })
      .catch(function () { window.location.href = '/'; });
  });

  // --- Delete account (multi-step: password → email code → delete) ---
  var deleteStepPassword = document.getElementById('delete-step-password');
  var deleteStepCode = document.getElementById('delete-step-code');
  var deleteCountdown = null;
  var deleteEmail = '';

  function resetDeleteFlow() {
    if (deleteCountdown) clearInterval(deleteCountdown);
    deleteStepPassword.hidden = true;
    deleteStepCode.hidden = true;
    document.getElementById('delete-password').value = '';
    document.getElementById('delete-code').value = '';
    document.getElementById('delete-msg').hidden = true;
    document.getElementById('delete-code-msg').hidden = true;
  }

  function startDeleteCountdown() {
    var remaining = 180;
    var timerEl = document.getElementById('delete-timer-countdown');
    var resendBtn = document.getElementById('btn-resend-delete-code');
    if (resendBtn) resendBtn.disabled = true;

    if (deleteCountdown) clearInterval(deleteCountdown);
    deleteCountdown = setInterval(function () {
      remaining--;
      var m = Math.floor(remaining / 60);
      var s = remaining % 60;
      if (timerEl) timerEl.textContent = m + ':' + (s < 10 ? '0' : '') + s;
      if (remaining <= 0) {
        clearInterval(deleteCountdown);
        if (timerEl) timerEl.textContent = 'expired';
        if (resendBtn) resendBtn.disabled = false;
      }
    }, 1000);
  }

  // Show password step
  document.getElementById('btn-show-delete').addEventListener('click', function () {
    resetDeleteFlow();
    deleteStepPassword.hidden = false;
  });

  // Cancel from password step
  document.getElementById('btn-cancel-delete').addEventListener('click', function () {
    resetDeleteFlow();
  });

  // Cancel from code step
  document.getElementById('btn-cancel-delete-code').addEventListener('click', function () {
    resetDeleteFlow();
  });

  // Step 1: Submit password → send code
  document.getElementById('btn-send-delete-code').addEventListener('click', function () {
    var password = document.getElementById('delete-password').value;
    var msgEl = document.getElementById('delete-msg');

    if (!password) {
      showMsg(msgEl, 'Please enter your password.', true);
      return;
    }

    var btn = document.getElementById('btn-send-delete-code');
    btn.disabled = true;
    btn.textContent = 'Sending code...';

    fetch(API_BASE + '/api/auth/delete-request', Object.assign({}, fetchOpts, {
      method: 'POST',
      body: JSON.stringify({ password: password }),
    }))
      .then(function (res) { return res.json().then(function (data) { return { ok: res.ok, data: data }; }); })
      .then(function (ref) {
        if (!ref.ok) {
          showMsg(msgEl, (ref.data.errors || ['Failed.']).join(' '), true);
          return;
        }
        // Move to code step
        deleteEmail = ref.data.email || '';
        deleteStepPassword.hidden = true;
        deleteStepCode.hidden = false;
        document.getElementById('delete-email-display').textContent = deleteEmail;
        startDeleteCountdown();
      })
      .catch(function (err) {
        reportProfile('profile.delete_request', err, { endpoint: '/api/auth/delete-request' });
        showMsg(msgEl, MSG_NET, true);
      })
      .finally(function () {
        btn.disabled = false;
        btn.textContent = 'Send Verification Code';
      });
  });

  // Resend delete code
  document.getElementById('btn-resend-delete-code').addEventListener('click', function () {
    var btn = document.getElementById('btn-resend-delete-code');
    btn.disabled = true;
    btn.textContent = 'Sending...';

    fetch(API_BASE + '/api/auth/resend-code', Object.assign({}, fetchOpts, {
      method: 'POST',
      body: JSON.stringify({ email: deleteEmail, purpose: 'delete' }),
    }))
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (data.ok) {
          startDeleteCountdown();
        } else {
          showMsg(document.getElementById('delete-code-msg'), (data.errors || ['Could not resend.']).join(' '), true);
        }
      })
      .catch(function (err) {
        reportProfile('profile.delete_resend', err, { endpoint: '/api/auth/resend-code' });
        showMsg(document.getElementById('delete-code-msg'), MSG_NET, true);
      })
      .finally(function () {
        btn.textContent = 'Resend Code';
      });
  });

  // Step 2: Submit code → delete account
  document.getElementById('btn-confirm-delete').addEventListener('click', function () {
    var code = (document.getElementById('delete-code').value || '').trim();
    var msgEl = document.getElementById('delete-code-msg');

    if (!code || code.length !== 6) {
      showMsg(msgEl, 'Please enter the 6-digit code.', true);
      return;
    }

    var btn = document.getElementById('btn-confirm-delete');
    btn.disabled = true;
    btn.textContent = 'Deleting...';

    fetch(API_BASE + '/api/auth/account', Object.assign({}, fetchOpts, {
      method: 'DELETE',
      body: JSON.stringify({ code: code }),
    }))
      .then(function (res) { return res.json().then(function (data) { return { ok: res.ok, data: data }; }); })
      .then(function (ref) {
        if (ref.ok) {
          window.location.href = '/';
        } else {
          showMsg(msgEl, (ref.data.errors || ['Failed to delete account.']).join(' '), true);
        }
      })
      .catch(function (err) {
        reportProfile('profile.account_delete', err, { endpoint: '/api/auth/account' });
        showMsg(msgEl, MSG_NET, true);
      })
      .finally(function () {
        btn.disabled = false;
        btn.textContent = 'Permanently Delete';
      });
  });
})();
