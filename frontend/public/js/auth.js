(function () {
  'use strict';

  var host = window.location.hostname;
  var API_BASE =
    host === 'localhost' || host === '127.0.0.1' ? 'http://127.0.0.1:5000' : '';

  var fetchOpts = {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
  };

  var errorEl = document.getElementById('auth-error');

  function showError(messages) {
    if (!errorEl) return;
    errorEl.hidden = false;
    errorEl.innerHTML = (Array.isArray(messages) ? messages : [messages])
      .map(function (m) { return '<div>' + m + '</div>'; })
      .join('');
  }

  function hideError() {
    if (errorEl) { errorEl.hidden = true; errorEl.innerHTML = ''; }
  }

  // ─── Password strength indicator ───
  var passwordInput = document.getElementById('password');
  var strengthFill = document.getElementById('strength-fill');
  var strengthLabel = document.getElementById('strength-label');

  function evaluateStrength(pw) {
    if (!pw) return null;
    var score = 0;
    if (pw.length >= 8) score++;
    if (pw.length >= 12) score++;
    if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) score++;
    if (/\d/.test(pw)) score++;
    if (/[^A-Za-z0-9]/.test(pw)) score++;

    if (score <= 1) return 'weak';
    if (score === 2) return 'fair';
    if (score === 3) return 'good';
    return 'strong';
  }

  if (passwordInput && strengthFill && strengthLabel) {
    passwordInput.addEventListener('input', function () {
      var level = evaluateStrength(passwordInput.value);
      strengthFill.className = 'strength-fill' + (level ? ' ' + level : '');
      strengthLabel.className = 'strength-label' + (level ? ' ' + level : '');
      strengthLabel.textContent = level || '';
    });
  }

  // ─── Confirm password match ───
  var confirmInput = document.getElementById('confirm-password');
  var confirmHint = document.getElementById('confirm-hint');

  function checkMatch() {
    if (!confirmInput || !confirmHint || !passwordInput) return;
    var pw = passwordInput.value;
    var cpw = confirmInput.value;
    if (!cpw) {
      confirmHint.textContent = '';
      confirmHint.className = 'field-hint';
      return;
    }
    if (pw === cpw) {
      confirmHint.textContent = 'Passwords match';
      confirmHint.className = 'field-hint match';
    } else {
      confirmHint.textContent = 'Passwords do not match';
      confirmHint.className = 'field-hint mismatch';
    }
  }

  if (confirmInput) {
    confirmInput.addEventListener('input', checkMatch);
  }
  if (passwordInput && confirmInput) {
    passwordInput.addEventListener('input', checkMatch);
  }

  // ─── Signup form ───
  var signupForm = document.getElementById('signup-form');
  if (signupForm) {
    signupForm.addEventListener('submit', function (e) {
      e.preventDefault();
      hideError();

      var email = (document.getElementById('email').value || '').trim();
      var username = (document.getElementById('username').value || '').trim();
      var password = document.getElementById('password').value || '';
      var confirmPassword = (document.getElementById('confirm-password').value || '');
      var acceptedTerms = document.getElementById('accept-terms').checked;

      // Client-side checks
      var errors = [];
      if (!email) errors.push('Email is required.');
      if (!username) errors.push('Username is required.');
      if (password.length < 8) errors.push('Password must be at least 8 characters.');
      if (password !== confirmPassword) errors.push('Passwords do not match.');
      if (!acceptedTerms) errors.push('You must accept the Terms of Service.');

      if (errors.length) { showError(errors); return; }

      var btn = document.getElementById('btn-signup');
      btn.disabled = true;
      btn.textContent = 'Creating account...';

      fetch(API_BASE + '/api/auth/signup', Object.assign({}, fetchOpts, {
        method: 'POST',
        body: JSON.stringify({
          email: email,
          username: username,
          password: password,
          confirmPassword: confirmPassword,
          acceptedTerms: acceptedTerms,
        }),
      }))
        .then(function (res) {
          return res.json().then(function (data) { return { ok: res.ok, data: data }; });
        })
        .then(function (ref) {
          if (!ref.ok) {
            showError(ref.data.errors || ['Something went wrong.']);
            return;
          }
          // Success — redirect to discover page
          window.location.href = 'discover.html';
        })
        .catch(function () {
          showError('Network error. Is the backend running on http://127.0.0.1:5000?');
        })
        .finally(function () {
          btn.disabled = false;
          btn.textContent = 'Create Account';
        });
    });
  }

  // ─── Login form ───
  var loginForm = document.getElementById('login-form');
  if (loginForm) {
    loginForm.addEventListener('submit', function (e) {
      e.preventDefault();
      hideError();

      var username = (document.getElementById('username').value || '').trim();
      var password = document.getElementById('password').value || '';

      if (!username || !password) {
        showError('Username and password are required.');
        return;
      }

      var btn = document.getElementById('btn-login');
      btn.disabled = true;
      btn.textContent = 'Signing in...';

      fetch(API_BASE + '/api/auth/login', Object.assign({}, fetchOpts, {
        method: 'POST',
        body: JSON.stringify({ username: username, password: password }),
      }))
        .then(function (res) {
          return res.json().then(function (data) { return { ok: res.ok, data: data }; });
        })
        .then(function (ref) {
          if (!ref.ok) {
            showError(ref.data.errors || ['Invalid username or password.']);
            return;
          }
          window.location.href = 'discover.html';
        })
        .catch(function () {
          showError('Network error. Is the backend running on http://127.0.0.1:5000?');
        })
        .finally(function () {
          btn.disabled = false;
          btn.textContent = 'Sign In';
        });
    });
  }
})();
