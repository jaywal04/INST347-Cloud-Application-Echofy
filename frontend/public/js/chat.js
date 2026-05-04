(function () {
  'use strict';

  function apiBase() {
    return typeof window.echofyApiBaseUrl === 'function'
      ? window.echofyApiBaseUrl()
      : String(window.ECHOFY_API_BASE || '').trim().replace(/\/+$/, '');
  }

  /* ── Inject panel into the page ──────────────────────────────────────── */
  var panelHtml =
    '<div id="echofy-ai-panel" class="echofy-ai-panel" role="dialog" aria-label="Echo AI" hidden>' +
      '<div class="echofy-ai-inner">' +
        '<div class="echofy-ai-header">' +
          '<span class="echofy-ai-title">Echo <em>AI</em></span>' +
          '<button class="echofy-ai-close" id="echofy-ai-close" aria-label="Close Echo AI">' +
            '<svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">' +
              '<path d="M18 6 6 18M6 6l12 12"/>' +
            '</svg>' +
          '</button>' +
        '</div>' +
        '<div id="echofy-ai-notice" class="echofy-ai-notice" hidden></div>' +
        '<div id="echofy-ai-chips" class="echofy-ai-chips">' +
          '<button class="echofy-ai-chip" data-prompt="What are the most popular reviews on Echofy right now?">What\'s trending?</button>' +
          '<button class="echofy-ai-chip" data-prompt="Summarize the top community reviews for me.">Top reviews</button>' +
          '<button class="echofy-ai-chip" data-prompt="Based on the community reviews, what music should I check out?">Music picks</button>' +
          '<button class="echofy-ai-chip" data-prompt="What genres or artists are people rating most highly?">Popular artists</button>' +
        '</div>' +
        '<div id="echofy-ai-messages" class="echofy-ai-messages" role="log" aria-live="polite"></div>' +
        '<form id="echofy-ai-form" class="echofy-ai-form" autocomplete="off">' +
          '<div class="echofy-ai-input-wrap">' +
            '<textarea id="echofy-ai-input" class="echofy-ai-input" placeholder="Ask about music, reviews…" rows="1" maxlength="1000" aria-label="Chat message"></textarea>' +
            '<button type="submit" id="echofy-ai-send" class="echofy-ai-send" aria-label="Send message">' +
              '<svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.2" viewBox="0 0 24 24">' +
                '<path d="M22 2 11 13M22 2 15 22 11 13 2 9l20-7Z"/>' +
              '</svg>' +
            '</button>' +
          '</div>' +
          '<p class="echofy-ai-hint">Uses community review data. Answers may not be accurate.</p>' +
        '</form>' +
      '</div>' +
    '</div>' +
    '<div id="echofy-ai-backdrop" class="echofy-ai-backdrop" hidden></div>';

  document.body.insertAdjacentHTML('beforeend', panelHtml);

  var panel      = document.getElementById('echofy-ai-panel');
  var backdrop   = document.getElementById('echofy-ai-backdrop');
  var closeBtn   = document.getElementById('echofy-ai-close');
  var noticeEl   = document.getElementById('echofy-ai-notice');
  var chipsEl    = document.getElementById('echofy-ai-chips');
  var messagesEl = document.getElementById('echofy-ai-messages');
  var formEl     = document.getElementById('echofy-ai-form');
  var inputEl    = document.getElementById('echofy-ai-input');
  var sendBtn    = document.getElementById('echofy-ai-send');

  var chatHistory    = [];
  var isLoading      = false;
  var isOpen         = false;
  var statusChecked  = false;
  var isConfigured   = false;
  var isAuthenticated = false;

  /* ── Panel open / close ───────────────────────────────────────────────── */
  function openPanel() {
    panel.hidden = false;
    backdrop.hidden = false;
    isOpen = true;
    requestAnimationFrame(function () {
      panel.classList.add('is-open');
      backdrop.classList.add('is-open');
    });
    checkStatus();
  }

  function closePanel() {
    panel.classList.remove('is-open');
    backdrop.classList.remove('is-open');
    isOpen = false;
    setTimeout(function () {
      if (!isOpen) {
        panel.hidden = true;
        backdrop.hidden = true;
      }
    }, 260);
  }

  closeBtn.addEventListener('click', closePanel);
  backdrop.addEventListener('click', closePanel);
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && isOpen) closePanel();
  });

  /* ── Wire the nav button (may not exist yet when this runs) ───────────── */
  function attachNavBtn(btn) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      isOpen ? closePanel() : openPanel();
    });
  }

  var existing = document.getElementById('echofy-ai-nav-btn');
  if (existing) {
    attachNavBtn(existing);
  } else {
    var observer = new MutationObserver(function () {
      var btn = document.getElementById('echofy-ai-nav-btn');
      if (btn) { attachNavBtn(btn); observer.disconnect(); }
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  /* ── Status / auth check ─────────────────────────────────────────────── */
  function checkStatus() {
    if (statusChecked) { applyStatus(); return; }
    Promise.all([
      fetch(apiBase() + '/api/chat/status')
        .then(function (r) { return r.json(); })
        .catch(function () { return { configured: false }; }),
      fetch(apiBase() + '/api/auth/me', { credentials: 'include' })
        .then(function (r) { return r.json(); })
        .catch(function () { return { authenticated: false }; }),
    ]).then(function (res) {
      isConfigured    = !!(res[0] && res[0].configured);
      isAuthenticated = !!(res[1] && res[1].authenticated);
      statusChecked   = true;
      applyStatus();
    });
  }

  function applyStatus() {
    noticeEl.hidden = true;
    noticeEl.innerHTML = '';
    formEl.hidden   = false;
    chipsEl.hidden  = false;

    if (!isConfigured) {
      noticeEl.innerHTML = 'Echo AI is not configured on this server yet.';
      noticeEl.hidden = false;
      formEl.hidden   = true;
      chipsEl.hidden  = true;
      return;
    }
    if (!isAuthenticated) {
      noticeEl.innerHTML = '<a href="/login">Sign in</a> to chat with Echo AI.';
      noticeEl.hidden = false;
      formEl.hidden   = true;
      chipsEl.hidden  = true;
      return;
    }
    setTimeout(function () { inputEl.focus(); }, 50);
  }

  /* ── Chat logic ──────────────────────────────────────────────────────── */
  function setLoading(on) {
    isLoading = on;
    sendBtn.disabled = on;
    inputEl.disabled = on;
  }

  function autoResize() {
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 140) + 'px';
  }

  function appendMessage(role, text) {
    var row = document.createElement('div');
    row.className = 'echofy-ai-msg echofy-ai-msg-' + role;
    var bubble = document.createElement('div');
    bubble.className = 'echofy-ai-bubble';
    bubble.textContent = text;
    row.appendChild(bubble);
    messagesEl.appendChild(row);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return row;
  }

  function appendThinking() {
    var row = document.createElement('div');
    row.className = 'echofy-ai-msg echofy-ai-msg-assistant';
    row.innerHTML = '<div class="echofy-ai-bubble echofy-ai-thinking"><span></span><span></span><span></span></div>';
    messagesEl.appendChild(row);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return row;
  }

  function send(message) {
    if (isLoading || !message.trim()) return;
    appendMessage('user', message);
    chatHistory.push({ role: 'user', content: message });
    inputEl.value = '';
    autoResize();
    chipsEl.hidden = true;
    setLoading(true);
    var thinkRow = appendThinking();

    fetch(apiBase() + '/api/chat', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: message, history: chatHistory.slice(0, -1) }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        thinkRow.remove();
        if (data.ok) {
          appendMessage('assistant', data.reply);
          chatHistory.push({ role: 'assistant', content: data.reply });
        } else {
          appendMessage('assistant', 'Error: ' + (data.error || 'something went wrong.'));
        }
      })
      .catch(function () {
        thinkRow.remove();
        appendMessage('assistant', 'Could not reach the server. Please try again.');
      })
      .finally(function () { setLoading(false); });
  }

  formEl.addEventListener('submit', function (e) {
    e.preventDefault();
    send(inputEl.value.trim());
  });
  inputEl.addEventListener('input', autoResize);
  inputEl.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(inputEl.value.trim()); }
  });
  chipsEl.addEventListener('click', function (e) {
    var chip = e.target.closest('.echofy-ai-chip');
    if (chip) send(chip.dataset.prompt);
  });
})();
