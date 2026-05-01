(function () {
  'use strict';

  var API_BASE = window.ECHOFY_API_BASE || '';

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
  var verifyCard = document.getElementById('verify-card');
  var signupCard = signupForm ? signupForm.closest('.auth-card') : null;
  var pendingEmail = '';
  var countdownInterval = null;

  function startCountdown() {
    var remaining = 180; // 3 minutes
    var timerEl = document.getElementById('timer-countdown');
    var resendBtn = document.getElementById('btn-resend-code');
    if (resendBtn) resendBtn.disabled = true;

    if (countdownInterval) clearInterval(countdownInterval);
    countdownInterval = setInterval(function () {
      remaining--;
      var m = Math.floor(remaining / 60);
      var s = remaining % 60;
      if (timerEl) timerEl.textContent = m + ':' + (s < 10 ? '0' : '') + s;
      if (remaining <= 0) {
        clearInterval(countdownInterval);
        if (timerEl) timerEl.textContent = 'expired';
        if (resendBtn) resendBtn.disabled = false;
      }
    }, 1000);
  }

  function showVerifyStep(email) {
    pendingEmail = email;
    if (signupCard) signupCard.hidden = true;
    if (verifyCard) {
      verifyCard.hidden = false;
      document.getElementById('verify-email-display').textContent = email;
      document.getElementById('verify-code').value = '';
      var verifyError = document.getElementById('verify-error');
      if (verifyError) { verifyError.hidden = true; verifyError.innerHTML = ''; }
    }
    startCountdown();
  }

  function showVerifyError(messages) {
    var el = document.getElementById('verify-error');
    if (!el) return;
    el.hidden = false;
    el.innerHTML = (Array.isArray(messages) ? messages : [messages])
      .map(function (m) { return '<div>' + m + '</div>'; })
      .join('');
  }

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
      btn.textContent = 'Sending code...';

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
          // Show verification step
          showVerifyStep(ref.data.email || email);
        })
        .catch(function () {
          showError(
            'Network error. Is the backend running on ' +
              (window.ECHOFY_API_BASE || 'http://localhost:5001') +
              '?'
          );
        })
        .finally(function () {
          btn.disabled = false;
          btn.textContent = 'Create Account';
        });
    });
  }

  // ─── Verify code form ───
  var verifyForm = document.getElementById('verify-form');
  if (verifyForm) {
    verifyForm.addEventListener('submit', function (e) {
      e.preventDefault();
      var code = (document.getElementById('verify-code').value || '').trim();
      var verifyError = document.getElementById('verify-error');
      if (verifyError) { verifyError.hidden = true; }

      if (!code || code.length !== 6) {
        showVerifyError('Please enter the 6-digit code.');
        return;
      }

      var btn = document.getElementById('btn-verify');
      btn.disabled = true;
      btn.textContent = 'Verifying...';

      fetch(API_BASE + '/api/auth/verify-signup', Object.assign({}, fetchOpts, {
        method: 'POST',
        body: JSON.stringify({ email: pendingEmail, code: code }),
      }))
        .then(function (res) {
          return res.json().then(function (data) { return { ok: res.ok, data: data }; });
        })
        .then(function (ref) {
          if (!ref.ok) {
            showVerifyError(ref.data.errors || ['Verification failed.']);
            return;
          }
          // Success — account created, redirect to username discovery (Discover page)
          var un = (ref.data.user && ref.data.user.username) || '';
          window.location.href = un
            ? '/' + encodeURIComponent(un) + '/discovery'
            : '/discover';
        })
        .catch(function () {
          showVerifyError('Network error.');
        })
        .finally(function () {
          btn.disabled = false;
          btn.textContent = 'Verify & Create Account';
        });
    });
  }

  // ─── Resend code ───
  var resendBtn = document.getElementById('btn-resend-code');
  if (resendBtn) {
    resendBtn.addEventListener('click', function () {
      resendBtn.disabled = true;
      resendBtn.textContent = 'Sending...';

      fetch(API_BASE + '/api/auth/resend-code', Object.assign({}, fetchOpts, {
        method: 'POST',
        body: JSON.stringify({ email: pendingEmail, purpose: 'signup' }),
      }))
        .then(function (res) { return res.json(); })
        .then(function (data) {
          if (data.ok) {
            startCountdown();
          } else {
            showVerifyError(data.errors || ['Could not resend code.']);
          }
        })
        .catch(function () {
          showVerifyError('Network error.');
        })
        .finally(function () {
          resendBtn.textContent = 'Resend Code';
        });
    });
  }

  // ─── Back to signup ───
  var backBtn = document.getElementById('btn-back-signup');
  if (backBtn) {
    backBtn.addEventListener('click', function () {
      if (countdownInterval) clearInterval(countdownInterval);
      if (verifyCard) verifyCard.hidden = true;
      if (signupCard) signupCard.hidden = false;
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
          var logged = (ref.data.user && ref.data.user.username) || '';
          window.location.href = logged
            ? '/' + encodeURIComponent(logged) + '/discovery'
            : '/discover';
        })
        .catch(function () {
          showError(
            'Network error. Is the backend running on ' +
              (window.ECHOFY_API_BASE || 'http://localhost:5001') +
              '?'
          );
        })
        .finally(function () {
          btn.disabled = false;
          btn.textContent = 'Sign In';
        });
    });
  }
})();
