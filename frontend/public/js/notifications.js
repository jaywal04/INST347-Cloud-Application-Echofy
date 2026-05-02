(function () {
  'use strict';

  var API_BASE = window.ECHOFY_API_BASE || '';
  var fetchOpts = { credentials: 'include', headers: { 'Content-Type': 'application/json' } };
  var MSG_NET =
    'Something went wrong. The team has been notified. Please try again shortly.';

  var listEl = document.getElementById('notif-requests');
  var emptyEl = document.getElementById('notif-empty');
  if (!listEl) return;

  function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function load() {
    fetch(API_BASE + '/api/friends/requests/incoming', Object.assign({}, fetchOpts, { method: 'GET' }))
      .then(function (res) {
        if (res.status === 401) {
          window.location.href = '/login';
          return null;
        }
        return res.json();
      })
      .then(function (data) {
        if (!data || !data.ok) return;
        var reqs = data.requests || [];
        listEl.innerHTML = '';
        if (reqs.length === 0) {
          emptyEl.hidden = false;
          return;
        }
        emptyEl.hidden = true;
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
          listEl.appendChild(li);
        });
      })
      .catch(function (err) {
        if (window.echofyReportClientBug) {
          window.echofyReportClientBug({
            scope: 'notifications.incoming_load',
            apiBasePresent: !!API_BASE,
            errorMessage: err && err.message ? String(err.message) : 'request_failed',
          });
        }
        if (emptyEl) {
          emptyEl.textContent = MSG_NET;
          emptyEl.hidden = false;
        }
      });
  }

  listEl.addEventListener('click', function (e) {
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
