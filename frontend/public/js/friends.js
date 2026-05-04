(function () {
  'use strict';

  var API_BASE = window.ECHOFY_API_BASE || '';
  var fetchOpts = { credentials: 'include', headers: { 'Content-Type': 'application/json' } };

  var myUserId = null;

  if (API_BASE) {
    fetch(API_BASE + '/api/auth/me', { credentials: 'include' })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data || !data.authenticated) {
          window.location.href = '/login';
          return;
        }
        myUserId = data.user && data.user.id;
      })
      .catch(function () { window.location.href = '/login'; });
  }
  var searchTimer = null;
  var MSG_NET =
    'Something went wrong. The team has been notified. Please try again shortly.';

  function reportFriends(scope, err, extra) {
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
          window.location.href = '/login';
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

  function loadFollowing() {
    return fetch(API_BASE + '/api/follows/following', Object.assign({}, fetchOpts, { method: 'GET' }))
      .then(function (res) {
        if (res.status === 401) return null;
        return res.json();
      });
  }

  var removeConfirmTimer = null;

  function resetRemoveBtn(btn) {
    if (removeConfirmTimer) { clearTimeout(removeConfirmTimer); removeConfirmTimer = null; }
    btn.textContent = 'Remove';
    btn.classList.remove('btn-danger');
    btn.classList.add('btn-ghost');
    btn.removeAttribute('data-confirming');
    btn.disabled = false;
  }

  function buildUserCard(f, extraBtn) {
    var li = document.createElement('li');
    li.className = 'friends-card';
    var link = document.createElement('a');
    link.className = 'friends-card-link';
    link.href =
      (typeof window.echofyUserPath === 'function'
        ? window.echofyUserPath('user')
        : '/user') + '?id=' + f.id;
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
    if (extraBtn) li.appendChild(extraBtn);
    return li;
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
      var removeBtn = document.createElement('button');
      removeBtn.type = 'button';
      removeBtn.className = 'btn-ghost btn-sm';
      removeBtn.setAttribute('data-remove-friend', f.id);
      removeBtn.textContent = 'Remove';
      ul.appendChild(buildUserCard(f, removeBtn));
    });
  }

  function renderFollowing(data) {
    var ul = document.getElementById('following-list');
    var empty = document.getElementById('following-list-empty');
    if (!data || !data.ok || !ul) return;
    var following = data.following || [];
    ul.innerHTML = '';
    if (following.length === 0) {
      empty.hidden = false;
      return;
    }
    empty.hidden = true;
    following.forEach(function (f) {
      var unfollowBtn = document.createElement('button');
      unfollowBtn.type = 'button';
      unfollowBtn.className = 'btn-ghost btn-sm';
      unfollowBtn.setAttribute('data-unfollow', f.id);
      unfollowBtn.textContent = 'Unfollow';
      ul.appendChild(buildUserCard(f, unfollowBtn));
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

  function updateMyStats(friendCount, followingCount) {
    if (!myUserId) return;
    fetch(API_BASE + '/api/users/' + myUserId + '/profile', Object.assign({}, fetchOpts, { method: 'GET' }))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data || !data.ok) return;
        document.getElementById('my-follower-count').textContent = data.profile.follower_count || 0;
        document.getElementById('my-friend-count').textContent = friendCount;
        document.getElementById('my-following-count').textContent = followingCount;
        document.getElementById('friends-my-stats').hidden = false;
      })
      .catch(function () {});
  }

  function refreshAll() {
    Promise.all([loadFriends(), loadIncoming(), loadOutgoing(), loadFollowing()]).then(function (results) {
      if (!results[0]) return;
      renderFriends(results[0]);
      renderIncoming(results[1] || { ok: true, requests: [] });
      renderOutgoing(results[2] || { ok: true, requests: [] });
      renderFollowing(results[3] || { ok: true, following: [] });
      var friendCount = (results[0].friends || []).length;
      var followingCount = (results[3] && results[3].following ? results[3].following.length : 0);
      updateMyStats(friendCount, followingCount);
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
          window.location.href = '/login';
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
          var followLabel = u.is_following ? 'Unfollow' : 'Follow';
          var followClass = u.is_following ? 'btn-ghost btn-sm' : 'btn-secondary btn-sm';
          li.innerHTML =
            '<span class="friends-search-name">' + escapeHtml(u.username) + '</span>' +
            '<div class="friends-search-actions">' +
            '<button type="button" class="btn-primary btn-sm" data-add-user="' + u.id + '">Add friend</button>' +
            '<button type="button" class="' + followClass + '" data-follow-user="' + u.id + '" data-following="' + (u.is_following ? '1' : '0') + '">' + followLabel + '</button>' +
            '</div>';
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
    var msgEl = document.getElementById('friend-search-msg');

    var addBtn = e.target.closest('[data-add-user]');
    if (addBtn) {
      var userId = parseInt(addBtn.getAttribute('data-add-user'), 10);
      addBtn.disabled = true;
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
        .catch(function (err) {
          reportFriends('friends.send_request', err, { endpoint: '/api/friends/requests' });
          showMsg(msgEl, MSG_NET, true);
        })
        .finally(function () {
          addBtn.disabled = false;
        });
      return;
    }

    var followBtn = e.target.closest('[data-follow-user]');
    if (followBtn) {
      var targetId = parseInt(followBtn.getAttribute('data-follow-user'), 10);
      var isFollowing = followBtn.getAttribute('data-following') === '1';
      followBtn.disabled = true;
      var req;
      if (isFollowing) {
        req = fetch(API_BASE + '/api/follows/' + targetId, Object.assign({}, fetchOpts, { method: 'DELETE' }));
      } else {
        req = fetch(API_BASE + '/api/follows', Object.assign({}, fetchOpts, {
          method: 'POST',
          body: JSON.stringify({ user_id: targetId }),
        }));
      }
      req
        .then(function (res) { return res.json(); })
        .then(function (data) {
          if (data.ok) {
            var nowFollowing = !isFollowing;
            followBtn.setAttribute('data-following', nowFollowing ? '1' : '0');
            followBtn.textContent = nowFollowing ? 'Unfollow' : 'Follow';
            followBtn.className = nowFollowing ? 'btn-ghost btn-sm' : 'btn-secondary btn-sm';
            refreshAll();
          }
        })
        .catch(function (err) {
          reportFriends('friends.follow_toggle', err);
        })
        .finally(function () {
          followBtn.disabled = false;
        });
    }
  });

  document.getElementById('friend-list').addEventListener('click', function (e) {
    var btn = e.target.closest('[data-remove-friend]');
    if (!btn) return;
    var userId = parseInt(btn.getAttribute('data-remove-friend'), 10);

    if (!btn.hasAttribute('data-confirming')) {
      var prev = document.querySelector('[data-remove-friend][data-confirming]');
      if (prev && prev !== btn) resetRemoveBtn(prev);
      btn.textContent = 'Confirm?';
      btn.classList.remove('btn-ghost');
      btn.classList.add('btn-danger');
      btn.setAttribute('data-confirming', '1');
      removeConfirmTimer = setTimeout(function () { resetRemoveBtn(btn); }, 4000);
      return;
    }

    if (removeConfirmTimer) { clearTimeout(removeConfirmTimer); removeConfirmTimer = null; }
    btn.disabled = true;
    fetch(API_BASE + '/api/friends/' + userId, Object.assign({}, fetchOpts, { method: 'DELETE' }))
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (data.ok) {
          refreshAll();
        } else {
          resetRemoveBtn(btn);
        }
      })
      .catch(function (err) {
        reportFriends('friends.remove_friend', err, { endpoint: '/api/friends/' + userId });
        resetRemoveBtn(btn);
      });
  });

  var followingListEl = document.getElementById('following-list');
  if (followingListEl) {
    followingListEl.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-unfollow]');
      if (!btn) return;
      var userId = parseInt(btn.getAttribute('data-unfollow'), 10);
      btn.disabled = true;
      fetch(API_BASE + '/api/follows/' + userId, Object.assign({}, fetchOpts, { method: 'DELETE' }))
        .then(function (res) { return res.json(); })
        .then(function (data) {
          if (data.ok) refreshAll();
          else btn.disabled = false;
        })
        .catch(function (err) {
          reportFriends('friends.unfollow', err);
          btn.disabled = false;
        });
    });
  }

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
