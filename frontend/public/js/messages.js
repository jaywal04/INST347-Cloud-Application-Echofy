(function () {
  'use strict';

  var API_BASE = typeof window.echofyApiBaseUrl === 'function'
    ? window.echofyApiBaseUrl()
    : String(window.ECHOFY_API_BASE || '').trim().replace(/\/+$/, '');
  var isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
  function route(path) {
    var raw = String(path || '').trim();
    if (!isLocal || !raw || raw === '#' || /^https?:\/\//.test(raw)) return raw;
    return raw.slice(-5) === '.html' ? raw : raw + '.html';
  }
  var fetchOpts = { credentials: 'include', headers: { 'Content-Type': 'application/json' } };
  var params = new URLSearchParams(window.location.search);

  var threadListEl = document.getElementById('message-thread-list');
  var threadEmptyEl = document.getElementById('message-thread-empty');
  var friendNameEl = document.getElementById('message-friend-name');
  var friendSubtitleEl = document.getElementById('message-friend-subtitle');
  var statusEl = document.getElementById('message-status');
  var messageListEl = document.getElementById('message-list');
  var formEl = document.getElementById('message-form');
  var textEl = document.getElementById('message-text');
  var shareSelectEl = document.getElementById('message-share-select');
  var sharePreviewEl = document.getElementById('message-share-preview');
  var sendButtonEl = document.getElementById('message-send-button');

  var selectedFriendId = params.get('friend') || '';
  var threads = [];
  var savedItems = [];
  var POLL_INTERVAL_MS = 2500;
  var pollTimer = null;
  var lastConversationSignature = '';

  if (!threadListEl || !messageListEl || !formEl) return;

  function escapeHtml(value) {
    var div = document.createElement('div');
    div.textContent = value == null ? '' : String(value);
    return div.innerHTML;
  }

  function setStatus(text, isError) {
    if (!statusEl) return;
    if (!text) {
      statusEl.hidden = true;
      statusEl.textContent = '';
      return;
    }
    statusEl.hidden = false;
    statusEl.textContent = text;
    statusEl.className = 'profile-msg ' + (isError ? 'msg-error' : 'msg-success');
  }

  function formatTime(value) {
    if (!value) return '';
    var date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleString([], {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    });
  }

  function subtitleForThread(thread) {
    if (thread.latest_message) return thread.latest_message;
    if (thread.latest_shared_item && thread.latest_shared_item.name) {
      return 'Shared: ' + thread.latest_shared_item.name;
    }
    return 'No messages yet.';
  }

  function renderThreads() {
    threadListEl.innerHTML = '';
    if (!threads.length) {
      threadEmptyEl.hidden = false;
      return;
    }
    threadEmptyEl.hidden = true;

    threads.forEach(function (thread) {
      var friend = thread.friend;
      var isActive = String(friend.id) === String(selectedFriendId);
      var initials = (friend.username || '?').substring(0, 2).toUpperCase();
      var hasMessages = !!thread.latest_at;

      var avatarHtml = friend.profile_image_url
        ? '<img class="messages-thread-avatar-img" src="' + escapeHtml(friend.profile_image_url) + '" alt=""/>'
        : '<div class="messages-thread-avatar-initials">' + escapeHtml(initials) + '</div>';

      var li = document.createElement('li');
      var button = document.createElement('button');
      button.type = 'button';
      button.className = 'messages-thread-button' + (isActive ? ' is-active' : '');
      button.setAttribute('data-friend-id', String(friend.id));
      button.innerHTML =
        '<div class="messages-thread-avatar">' + avatarHtml + '</div>' +
        '<div class="messages-thread-info">' +
          '<div class="messages-thread-top">' +
            '<span class="messages-thread-name">' + escapeHtml(friend.username) + '</span>' +
            (thread.unread_count ? '<span class="messages-thread-badge">' + thread.unread_count + '</span>' : '') +
            (hasMessages ? '<span class="messages-thread-time">' + escapeHtml(formatTime(thread.latest_at)) + '</span>' : '') +
          '</div>' +
          '<div class="messages-thread-preview' + (!hasMessages ? ' messages-thread-new' : '') + '">' +
            escapeHtml(hasMessages ? subtitleForThread(thread) : 'Start a conversation') +
          '</div>' +
        '</div>';
      li.appendChild(button);
      threadListEl.appendChild(li);
    });
  }

  function renderSharedItem(item) {
    if (!item || !item.name) return '';
    var image = item.image
      ? '<img class="message-shared-image" src="' + escapeHtml(item.image) + '" alt=""/>'
      : '';
    var subtitle = [item.artists && item.artists.length ? item.artists.join(', ') : '', item.album || '']
      .filter(Boolean)
      .join(' · ');
    return (
      '<div class="message-shared-item">' +
        image +
        '<div class="message-shared-meta">' +
          '<div class="message-shared-title">' + escapeHtml(item.name) + '</div>' +
          (subtitle ? '<div class="message-shared-subtitle">' + escapeHtml(subtitle) + '</div>' : '') +
          (item.url ? '<a class="message-shared-link" href="' + escapeHtml(item.url) + '" target="_blank" rel="noopener noreferrer">Open on Spotify</a>' : '') +
        '</div>' +
      '</div>'
    );
  }

  function renderMessages(messages) {
    messageListEl.innerHTML = '';
    if (!messages.length) {
      messageListEl.innerHTML = '<div class="echo-empty">No messages yet. Say hi or share a song.</div>';
      return;
    }

    messages.forEach(function (message) {
      var bubble = document.createElement('div');
      bubble.className = 'message-bubble ' + (message.is_mine ? 'is-mine' : 'is-theirs');
      bubble.innerHTML =
        (message.text ? '<p class="message-text">' + escapeHtml(message.text) + '</p>' : '') +
        renderSharedItem(message.shared_item) +
        '<div class="message-time">' + escapeHtml(formatTime(message.created_at)) + '</div>';
      messageListEl.appendChild(bubble);
    });

    messageListEl.scrollTop = messageListEl.scrollHeight;
  }

  function conversationSignature(messages) {
    if (!Array.isArray(messages) || !messages.length) return 'empty';
    var last = messages[messages.length - 1] || {};
    return String(messages.length) + ':' + String(last.id || '') + ':' + String(last.created_at || '');
  }

  function setSelection(friend) {
    if (!friend) {
      selectedFriendId = '';
      friendNameEl.textContent = 'Pick a friend';
      friendSubtitleEl.textContent = 'Choose an accepted friend to open your conversation.';
      formEl.hidden = true;
      messageListEl.innerHTML = '<div class="echo-empty">No conversation selected yet.</div>';
      renderThreads();
      return;
    }

    selectedFriendId = String(friend.id);
    friendNameEl.textContent = friend.username;
    friendSubtitleEl.textContent = 'Only you and ' + friend.username + ' can see this conversation.';
    formEl.hidden = false;
    renderThreads();
  }

  function loadThreads() {
    return fetch(API_BASE + '/api/messages/threads', fetchOpts)
      .then(function (res) {
        if (res.status === 401) {
          window.location.href = route('login');
          return null;
        }
        return res.json().then(function (data) {
          return { ok: res.ok, status: res.status, data: data };
        });
      })
      .then(function (result) {
        if (!result) return null;
        if (result.ok && result.data && result.data.ok) {
          threads = result.data.threads || [];
          renderThreads();
          return { source: 'threads' };
        }
        return loadThreadsFallbackFriends(result.status);
      })
      .catch(function () {
        return loadThreadsFallbackFriends(0);
      });
  }

  function mapFriendToThread(friend) {
    return {
      friend: {
        id: friend.id,
        username: friend.username || 'Unknown',
        profile_image_url: friend.profile_image_url || ''
      },
      latest_at: null,
      latest_message: null,
      latest_shared_item: null,
      unread_count: 0
    };
  }

  function loadThreadsFallbackFriends(failedStatus) {
    return fetch(API_BASE + '/api/friends', fetchOpts)
      .then(function (res) {
        if (res.status === 401) {
          window.location.href = route('login');
          return null;
        }
        return res.json().then(function (data) {
          return { ok: res.ok, data: data };
        });
      })
      .then(function (fallbackResult) {
        if (!fallbackResult) return null;
        if (!fallbackResult.ok || !fallbackResult.data || !fallbackResult.data.ok) {
          setStatus('Could not load your friends for messaging right now.', true);
          threads = [];
          renderThreads();
          return null;
        }
        threads = (fallbackResult.data.friends || []).map(mapFriendToThread);
        setStatus(
          failedStatus
            ? 'Loaded friends list. Recent message previews are temporarily unavailable.'
            : 'Loaded friends list from fallback source.',
          false
        );
        renderThreads();
        return { source: 'friends_fallback' };
      });
  }

  function loadSavedItems() {
    return fetch(API_BASE + '/api/reviews/saved', fetchOpts)
      .then(function (res) {
        if (res.status === 401) return null;
        return res.json().then(function (data) {
          return { ok: res.ok, status: res.status, data: data };
        });
      })
      .then(function (result) {
        if (!result || !result.ok || !result.data || !result.data.ok) return null;
        savedItems = (result.data.items || []).map(function (entry) {
          if (!entry || !entry.item) return null;
          return {
            item_key: entry.item_key || '',
            type: entry.item.type || 'track',
            name: entry.item.name || '',
            artists: entry.item.artists || [],
            album: entry.item.album || '',
            image: entry.item.image || '',
            url: entry.item.url || ''
          };
        }).filter(Boolean);

        if (!shareSelectEl) return;
        shareSelectEl.innerHTML = '<option value="">No song selected</option>';
        savedItems.forEach(function (item) {
          var option = document.createElement('option');
          option.value = item.item_key;
          option.textContent = item.name + (item.artists.length ? ' — ' + item.artists.join(', ') : '');
          shareSelectEl.appendChild(option);
        });
      })
      .catch(function () {
        // Saved song sharing is optional; keep Messages usable on fetch failures.
        savedItems = [];
        if (shareSelectEl) {
          shareSelectEl.innerHTML = '<option value="">No song selected</option>';
        }
        return null;
      });
  }

  function updateSharePreview() {
    if (!shareSelectEl || !sharePreviewEl) return;
    var key = shareSelectEl.value;
    var item = savedItems.find(function (candidate) {
      return candidate.item_key === key;
    });
    if (!item) {
      sharePreviewEl.hidden = true;
      sharePreviewEl.innerHTML = '';
      return;
    }
    sharePreviewEl.hidden = false;
    sharePreviewEl.innerHTML =
      '<div class="message-share-preview-title">' + escapeHtml(item.name) + '</div>' +
      '<div class="message-share-preview-subtitle">' + escapeHtml((item.artists || []).join(', ') + (item.album ? ' · ' + item.album : '')) + '</div>';
  }

  function refreshNavBadge() {
    fetch(API_BASE + '/api/messages/unread-count', { credentials: 'include' })
      .then(function (res) { return res.json(); })
      .then(function (d) {
        var badge = document.getElementById('nav-messages-badge');
        if (!d || !d.ok) return;
        if (d.count > 0) {
          if (badge) {
            badge.textContent = d.count > 99 ? '99+' : String(d.count);
          }
        } else if (badge) {
          badge.remove();
        }
      })
      .catch(function () {});
  }

  function openConversation(friendId, opts) {
    if (!friendId) return;
    opts = opts || {};
    var silent = !!opts.silent;
    if (!silent) setStatus('', false);
    fetch(API_BASE + '/api/messages/conversations/' + encodeURIComponent(friendId), fetchOpts)
      .then(function (res) {
        if (res.status === 401) {
          window.location.href = route('login');
          return null;
        }
        return res.json().then(function (data) {
          return { ok: res.ok, status: res.status, data: data };
        });
      })
      .then(function (result) {
        if (!result) return;
        if (!result.ok) {
          setSelection(null);
          if (!silent) {
            setStatus((result.data.errors || ['Could not load this conversation.']).join(' '), true);
          }
          return;
        }
        setSelection(result.data.friend);
        var nextMessages = result.data.messages || [];
        var sig = conversationSignature(nextMessages);
        if (sig !== lastConversationSignature) {
          renderMessages(nextMessages);
          lastConversationSignature = sig;
        }
        if (!silent && textEl) textEl.focus();
        loadThreads();
        refreshNavBadge();
      })
      .catch(function () {
        if (!silent) {
          setStatus('Network error while loading this conversation.', true);
        }
      });
  }

  function startLiveUpdates() {
    stopLiveUpdates();
    pollTimer = window.setInterval(function () {
      if (document.hidden) return;
      loadThreads();
      refreshNavBadge();
      if (selectedFriendId) {
        openConversation(selectedFriendId, { silent: true });
      }
    }, POLL_INTERVAL_MS);
  }

  function stopLiveUpdates() {
    if (!pollTimer) return;
    window.clearInterval(pollTimer);
    pollTimer = null;
  }

  threadListEl.addEventListener('click', function (event) {
    var button = event.target.closest('[data-friend-id]');
    if (!button) return;
    openConversation(button.getAttribute('data-friend-id'));
  });

  if (shareSelectEl) {
    shareSelectEl.addEventListener('change', updateSharePreview);
  }

  if (textEl) {
    textEl.addEventListener('keydown', function (event) {
      if (event.key !== 'Enter' || event.shiftKey) return;
      event.preventDefault();
      formEl.requestSubmit();
    });
  }

  formEl.addEventListener('submit', function (event) {
    event.preventDefault();
    if (!selectedFriendId) {
      setStatus('Choose a friend first.', true);
      return;
    }

    var text = (textEl.value || '').trim();
    var sharedItem = null;
    if (shareSelectEl && shareSelectEl.value) {
      sharedItem = savedItems.find(function (candidate) {
        return candidate.item_key === shareSelectEl.value;
      }) || null;
    }

    if (!text && !sharedItem) {
      setStatus('Write a message or share a saved song.', true);
      return;
    }

    sendButtonEl.disabled = true;
    sendButtonEl.textContent = 'Sending...';

    fetch(API_BASE + '/api/messages/conversations/' + encodeURIComponent(selectedFriendId), {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: text,
        shared_item: sharedItem
      })
    })
      .then(function (res) {
        if (res.status === 401) {
          window.location.href = route('login');
          return null;
        }
        return res.json().then(function (data) {
          return { ok: res.ok, data: data };
        });
      })
      .then(function (result) {
        if (!result) return;
        if (!result.ok) {
          setStatus((result.data.errors || ['Could not send this message.']).join(' '), true);
          return;
        }
        textEl.value = '';
        if (shareSelectEl) {
          shareSelectEl.value = '';
          updateSharePreview();
        }
        setStatus('Message sent.', false);
        openConversation(selectedFriendId);
      })
      .catch(function () {
        setStatus('Network error while sending your message.', true);
      })
      .finally(function () {
        sendButtonEl.disabled = false;
        sendButtonEl.textContent = 'Send message';
      });
  });

  fetch(API_BASE + '/api/auth/me', { credentials: 'include' })
    .then(function (res) { return res.json(); })
    .then(function (data) {
      if (data.authenticated && data.user && data.user.username) {
        var target = '/' + encodeURIComponent(data.user.username) + '/messages';
        if (window.location.pathname !== target) {
          history.replaceState(null, '', target + window.location.search);
        }
      }
    })
    .catch(function () {});

  Promise.all([loadThreads(), loadSavedItems()])
    .then(function () {
      if (selectedFriendId) {
        openConversation(selectedFriendId);
        return;
      }
      if (threads.length) {
        openConversation(threads[0].friend.id);
      }
    })
    .catch(function () {
      setStatus('Could not finish loading Messages. Please refresh and try again.', true);
    });

  startLiveUpdates();
  window.addEventListener('beforeunload', stopLiveUpdates);
})();
