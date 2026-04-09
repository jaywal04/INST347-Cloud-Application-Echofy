(function () {
  'use strict';

  var API_BASE = window.ECHOFY_API_BASE || '';
  var fetchOpts = { credentials: 'include', headers: { 'Content-Type': 'application/json' } };
  var searchTimer = null;

  function showMsg(el, text, isError) {
    if (!el) return;
    el.hidden = false;
    el.textContent = text;
    el.className = 'profile-msg friends-inline-msg ' + (isError ? 'msg-error' : 'msg-success');
    setTimeout(function () { el.hidden = true; }, 4000);
  }

  function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function loadFriends() {
    return fetch(API_BASE + '/api/friends', Object.assign({}, fetchOpts, { method: 'GET' }))
      .then(function (res) {
        if (res.status === 401) {
          window.location.href = 'login';
          return null;
        }
        return res.json();
      });
  }

  function loadIncoming() {
    return fetch(API_BASE + '/api/friends/requests/incoming', Object.assign({}, fetchOpts, { method: 'GET' }))
      .then(function (res) {
        if (res.status === 401) return null;
        return res.json();
      });
  }

  function loadOutgoing() {
    return fetch(API_BASE + '/api/friends/requests/outgoing', Object.assign({}, fetchOpts, { method: 'GET' }))
      .then(function (res) {
        if (res.status === 401) return null;
        return res.json();
      });
  }

  function renderFriends(data) {
    var ul = document.getElementById('friend-list');
    var empty = document.getElementById('friend-list-empty');
    if (!data || !data.ok) return;
    var friends = data.friends || [];
    ul.innerHTML = '';
    if (friends.length === 0) {
      empty.hidden = false;
      return;
    }
    empty.hidden = true;
    friends.forEach(function (f) {
      var li = document.createElement('li');
      li.className = 'friends-card';
      var link = document.createElement('a');
      link.className = 'friends-card-link';
      link.href = 'user?id=' + f.id;
      if (f.profile_image_url) {
        var img = document.createElement('img');
        img.className = 'friends-card-img';
        img.alt = '';
        img.src = f.profile_image_url;
        link.appendChild(img);
      } else {
        var initials = document.createElement('div');
        initials.className = 'friends-card-initials';
        initials.textContent = f.username.substring(0, 2).toUpperCase();
        link.appendChild(initials);
      }
      var name = document.createElement('span');
      name.className = 'friends-card-name';
      name.textContent = f.username;
      link.appendChild(name);
      li.appendChild(link);
      ul.appendChild(li);
    });
  }

  function renderIncoming(data) {
    var ul = document.getElementById('friend-incoming-list');
    var empty = document.getElementById('friend-incoming-empty');
    if (!data || !data.ok) return;
    var reqs = data.requests || [];
    ul.innerHTML = '';
    if (reqs.length === 0) {
      empty.hidden = false;
      return;
    }
    empty.hidden = true;
    reqs.forEach(function (r) {
      var li = document.createElement('li');
      li.className = 'friends-request-row';
      li.innerHTML =
        '<span class="friends-request-user">' + escapeHtml(r.from_user.username) + '</span>' +
        '<div class="friends-request-actions">' +
        '<button type="button" class="btn-primary btn-sm" data-accept="' + r.id + '">Accept</button>' +
        '<button type="button" class="btn-ghost btn-sm" data-decline="' + r.id + '">Decline</button>' +
        '</div>';
      ul.appendChild(li);
    });
  }

  function renderOutgoing(data) {
    var ul = document.getElementById('friend-outgoing-list');
    var empty = document.getElementById('friend-outgoing-empty');
    if (!data || !data.ok) return;
    var reqs = data.requests || [];
    ul.innerHTML = '';
    if (reqs.length === 0) {
      empty.hidden = false;
      return;
    }
    empty.hidden = true;
    reqs.forEach(function (r) {
      var li = document.createElement('li');
      li.className = 'friends-request-row';
      li.innerHTML =
        '<span class="friends-request-user">Pending — ' + escapeHtml(r.to_user.username) + '</span>';
      ul.appendChild(li);
    });
  }

  function refreshAll() {
    Promise.all([loadFriends(), loadIncoming(), loadOutgoing()]).then(function (results) {
      if (!results[0]) return;
      renderFriends(results[0]);
      renderIncoming(results[1] || { ok: true, requests: [] });
      renderOutgoing(results[2] || { ok: true, requests: [] });
    });
  }

  function runSearch(q) {
    var ul = document.getElementById('friend-search-results');
    var empty = document.getElementById('friend-search-empty');
    if (q.length < 2) {
      ul.hidden = true;
      empty.hidden = true;
      ul.innerHTML = '';
      return;
    }
    fetch(API_BASE + '/api/users/search?q=' + encodeURIComponent(q), Object.assign({}, fetchOpts, { method: 'GET' }))
      .then(function (res) {
        if (res.status === 401) {
          window.location.href = 'login';
          return null;
        }
        return res.json();
      })
      .then(function (data) {
        if (!data || !data.ok) return;
        var users = data.users || [];
        ul.innerHTML = '';
        if (users.length === 0) {
          ul.hidden = true;
          empty.hidden = false;
          return;
        }
        empty.hidden = true;
        ul.hidden = false;
        users.forEach(function (u) {
          var li = document.createElement('li');
          li.className = 'friends-search-row';
          li.innerHTML =
            '<span class="friends-search-name">' + escapeHtml(u.username) + '</span>' +
            '<button type="button" class="btn-primary btn-sm" data-add-user="' + u.id + '">Add friend</button>';
          ul.appendChild(li);
        });
      });
  }

  document.getElementById('friend-search-input').addEventListener('input', function () {
    var q = this.value.trim();
    if (searchTimer) clearTimeout(searchTimer);
    searchTimer = setTimeout(function () { runSearch(q); }, 300);
  });


  document.getElementById('friend-search-results').addEventListener('click', function (e) {
    var btn = e.target.closest('[data-add-user]');
    if (!btn) return;
    var userId = parseInt(btn.getAttribute('data-add-user'), 10);
    var msgEl = document.getElementById('friend-search-msg');
    btn.disabled = true;
    fetch(API_BASE + '/api/friends/requests', Object.assign({}, fetchOpts, {
      method: 'POST',
      body: JSON.stringify({ user_id: userId }),
    }))
      .then(function (res) { return res.json().then(function (data) { return { res: res, data: data }; }); })
      .then(function (x) {
        if (x.data.ok) {
          if (x.data.auto_accepted) {
            showMsg(msgEl, 'You are now friends.', false);
          } else if (x.data.already_pending) {
            showMsg(msgEl, 'Request already sent.', false);
          } else {
            showMsg(msgEl, 'Friend request sent.', false);
          }
          refreshAll();
          runSearch(document.getElementById('friend-search-input').value.trim());
        } else {
          showMsg(msgEl, (x.data.errors || ['Could not send request.']).join(' '), true);
        }
      })
      .catch(function () {
        showMsg(msgEl, 'Network error.', true);
      })
      .finally(function () {
        btn.disabled = false;
      });
  });

  document.getElementById('friend-incoming-list').addEventListener('click', function (e) {
    var acceptId = e.target.getAttribute('data-accept');
    var declineId = e.target.getAttribute('data-decline');
    var id = acceptId || declineId;
    if (!id) return;
    var path = acceptId ? '/accept' : '/decline';
    fetch(API_BASE + '/api/friends/requests/' + id + path, Object.assign({}, fetchOpts, { method: 'POST' }))
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (data.ok) refreshAll();
      });
  });

  refreshAll();
})();
