(function () {
  'use strict';

  var API_BASE = window.ECHOFY_API_BASE || '';
  var fetchOpts = { credentials: 'include', headers: { 'Content-Type': 'application/json' } };
  var MSG_NET =
    'Something went wrong. The team has been notified. Please try again shortly.';

  var requestListEl = document.getElementById('notif-requests');
  var reqEmptyEl = document.getElementById('notif-req-empty');
  var activityListEl = document.getElementById('notif-activity');
  var activityEmptyEl = document.getElementById('notif-activity-empty');
  if (!requestListEl) return;

  function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function timeAgo(isoStr) {
    if (!isoStr) return '';
    var diff = Math.floor((Date.now() - new Date(isoStr + 'Z').getTime()) / 1000);
    if (diff < 60) return 'just now';
    if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
    if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
    return Math.floor(diff / 86400) + 'd ago';
  }

  function loadRequests() {
    return fetch(API_BASE + '/api/friends/requests/incoming', Object.assign({}, fetchOpts, { method: 'GET' }))
      .then(function (res) {
        if (res.status === 401) { window.location.href = '/login'; return null; }
        return res.json();
      });
  }

  function loadActivity() {
    return fetch(API_BASE + '/api/notifications', Object.assign({}, fetchOpts, { method: 'GET' }))
      .then(function (res) {
        if (res.status === 401) return null;
        return res.json();
      });
  }

  function markAllRead() {
    fetch(API_BASE + '/api/notifications/read', Object.assign({}, fetchOpts, { method: 'POST' }))
      .catch(function () {});
  }

  function renderRequests(data) {
    if (!data || !data.ok) return;
    var reqs = data.requests || [];
    requestListEl.innerHTML = '';
    if (reqs.length === 0) {
      if (reqEmptyEl) reqEmptyEl.hidden = false;
      return;
    }
    if (reqEmptyEl) reqEmptyEl.hidden = true;
    reqs.forEach(function (r) {
      var li = document.createElement('li');
      li.className = 'friends-request-row';
      li.innerHTML =
        '<span class="friends-request-user">' +
          '<strong>' + escapeHtml(r.from_user.username) + '</strong> sent you a friend request' +
        '</span>' +
        '<div class="friends-request-actions">' +
          '<button type="button" class="btn-primary btn-sm" data-accept="' + r.id + '">Accept</button>' +
          '<button type="button" class="btn-ghost btn-sm" data-decline="' + r.id + '">Decline</button>' +
        '</div>';
      requestListEl.appendChild(li);
    });
  }

  function renderActivity(data) {
    if (!activityListEl) return;
    if (!data || !data.ok) return;
    var notifs = data.notifications || [];
    activityListEl.innerHTML = '';
    if (notifs.length === 0) {
      if (activityEmptyEl) activityEmptyEl.hidden = false;
      return;
    }
    if (activityEmptyEl) activityEmptyEl.hidden = true;
    notifs.forEach(function (n) {
      var li = document.createElement('li');
      li.className = 'notif-activity-row' + (n.read ? '' : ' notif-unread');
      var reviewHtml = '';
      if (n.review) {
        var reviewPath = (typeof window.echofyUserPath === 'function'
          ? window.echofyUserPath('review')
          : '/review');
        reviewHtml =
          ' &mdash; <a class="notif-review-link" href="' + reviewPath + '">' +
          escapeHtml(n.review.name) +
          ' (' + escapeHtml(String(n.review.rating)) + '/5)' +
          '</a>';
      }
      li.innerHTML =
        '<span class="notif-activity-text">' +
          '<strong>' + escapeHtml(n.actor ? n.actor.username : 'Someone') + '</strong>' +
          ' posted a new review' + reviewHtml +
        '</span>' +
        '<span class="notif-activity-time">' + escapeHtml(timeAgo(n.created_at)) + '</span>';
      activityListEl.appendChild(li);
    });
  }

  function load() {
    Promise.all([loadRequests(), loadActivity()]).then(function (results) {
      renderRequests(results[0]);
      renderActivity(results[1]);
      if (results[1] && results[1].ok) markAllRead();
    }).catch(function (err) {
      if (window.echofyReportClientBug) {
        window.echofyReportClientBug({
          scope: 'notifications.load',
          apiBasePresent: !!API_BASE,
          errorMessage: err && err.message ? String(err.message) : 'request_failed',
        });
      }
    });
  }

  requestListEl.addEventListener('click', function (e) {
    var acceptId = e.target.getAttribute('data-accept');
    var declineId = e.target.getAttribute('data-decline');
    var id = acceptId || declineId;
    if (!id) return;
    var path = acceptId ? '/accept' : '/decline';
    e.target.disabled = true;
    fetch(API_BASE + '/api/friends/requests/' + id + path, Object.assign({}, fetchOpts, { method: 'POST' }))
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (data.ok) load();
      });
  });

  load();
})();
