(function () {
  'use strict';

  var API_BASE = window.ECHOFY_API_BASE || '';
  var route = window.ECHOFY_ROUTE || function (value) { return value; };
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
      var li = document.createElement('li');
      var button = document.createElement('button');
      button.type = 'button';
      button.className = 'messages-thread-button' + (String(friend.id) === String(selectedFriendId) ? ' is-active' : '');
      button.setAttribute('data-friend-id', String(friend.id));
      button.innerHTML =
        '<div class="messages-thread-top">' +
          '<span class="messages-thread-name">' + escapeHtml(friend.username) + '</span>' +
          (thread.unread_count ? '<span class="messages-thread-badge">' + escapeHtml(thread.unread_count) + '</span>' : '') +
        '</div>' +
        '<div class="messages-thread-preview">' + escapeHtml(subtitleForThread(thread)) + '</div>' +
        (thread.latest_at ? '<div class="messages-thread-time">' + escapeHtml(formatTime(thread.latest_at)) + '</div>' : '');
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
        return res.json();
      })
      .then(function (data) {
        if (!data || !data.ok) return null;
        threads = data.threads || [];
        renderThreads();
        return data;
      });
  }

  function loadSavedItems() {
    return fetch(API_BASE + '/api/reviews/saved', fetchOpts)
      .then(function (res) {
        if (res.status === 401) return null;
        return res.json();
      })
      .then(function (data) {
        if (!data || !data.ok) return null;
        savedItems = (data.items || []).map(function (entry) {
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

  function openConversation(friendId) {
    if (!friendId) return;
    setStatus('', false);
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
          setStatus((result.data.errors || ['Could not load this conversation.']).join(' '), true);
          return;
        }
        setSelection(result.data.friend);
        renderMessages(result.data.messages || []);
        if (textEl) textEl.focus();
        loadThreads();
      })
      .catch(function () {
        setStatus('Network error while loading this conversation.', true);
      });
  }

  threadListEl.addEventListener('click', function (event) {
    var button = event.target.closest('[data-friend-id]');
    if (!button) return;
    openConversation(button.getAttribute('data-friend-id'));
  });

  if (shareSelectEl) {
    shareSelectEl.addEventListener('change', updateSharePreview);
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

  Promise.all([loadThreads(), loadSavedItems()]).then(function () {
    if (selectedFriendId) {
      openConversation(selectedFriendId);
      return;
    }
    if (threads.length) {
      openConversation(threads[0].friend.id);
    }
  });
})();
