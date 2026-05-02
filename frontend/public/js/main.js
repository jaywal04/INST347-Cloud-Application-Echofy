(function () {
  'use strict';

  var API_BASE = window.ECHOFY_API_BASE || '';
  var ART_COLORS = ['c1', 'c2', 'c3', 'c4', 'c5', 'c6'];

  function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = String(s);
    return d.innerHTML;
  }

  function timeAgo(iso) {
    if (!iso) return '';
    var then = new Date(iso.indexOf('Z') === -1 ? iso + 'Z' : iso);
    var secs = Math.floor((Date.now() - then) / 1000);
    if (secs < 60) return 'just now';
    var mins = Math.floor(secs / 60);
    if (mins < 60) return mins + (mins === 1 ? ' minute' : ' minutes') + ' ago';
    var hrs = Math.floor(mins / 60);
    if (hrs < 24) return hrs + (hrs === 1 ? ' hour' : ' hours') + ' ago';
    var days = Math.floor(hrs / 24);
    if (days === 1) return 'Yesterday';
    if (days < 7) return days + ' days ago';
    return then.toLocaleDateString();
  }

  function starsHtml(rating) {
    var html = '';
    for (var i = 1; i <= 5; i++) {
      html += '<span class="star' + (i > rating ? ' empty' : '') + '">★</span>';
    }
    return html;
  }

  function renderRecentReviews(reviews) {
    var list = document.getElementById('recent-reviews-list');
    var emptyEl = document.getElementById('recent-reviews-empty');
    if (!list) return;

    list.innerHTML = '';

    if (!reviews || reviews.length === 0) {
      if (emptyEl) emptyEl.hidden = false;
      return;
    }
    if (emptyEl) emptyEl.hidden = true;

    reviews.forEach(function (r, idx) {
      var item = r.item || {};
      var initials = (r.username || '?').substring(0, 2).toUpperCase();
      var trackName = item.name || '';
      var artists = (item.artists || []).join(', ');
      var label = trackName + (artists ? ' — ' + artists : '');

      var artDiv = document.createElement('div');
      artDiv.className = 'review-art';
      if (item.image) {
        artDiv.style.backgroundImage = 'url("' + item.image.replace(/"/g, '%22') + '")';
        artDiv.style.backgroundSize = 'cover';
        artDiv.style.backgroundPosition = 'center';
      } else {
        artDiv.classList.add(ART_COLORS[idx % ART_COLORS.length]);
        artDiv.textContent = '♪';
      }

      var bodyDiv = document.createElement('div');
      bodyDiv.className = 'review-body';
      bodyDiv.innerHTML =
        '<div class="review-top">' +
          '<div class="avatar">' + escapeHtml(initials) + '</div>' +
          '<span class="review-user">' + escapeHtml(r.username || '') + '</span>' +
          '<span class="review-action">reviewed</span>' +
          '<span class="review-album-name">' + escapeHtml(label) + '</span>' +
          '<div class="review-stars">' + starsHtml(r.rating) + '</div>' +
        '</div>' +
        (r.text ? '<p class="review-text">' + escapeHtml(r.text) + '</p>' : '') +
        '<div class="review-time">' + timeAgo(r.updated_at) + '</div>';

      var card = document.createElement('div');
      card.className = 'review-item';
      card.appendChild(artDiv);
      card.appendChild(bodyDiv);
      list.appendChild(card);
    });
  }

  var reviewsListEl = document.getElementById('recent-reviews-list');
  if (reviewsListEl) {
    fetch((API_BASE || '') + '/api/reviews/recent')
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (data && data.ok) {
          renderRecentReviews(data.reviews);
        } else {
          var emptyEl = document.getElementById('recent-reviews-empty');
          if (emptyEl) emptyEl.hidden = false;
        }
      })
      .catch(function (err) {
        console.error('[Echofy] /api/reviews/recent failed', err);
        var emptyEl = document.getElementById('recent-reviews-empty');
        if (emptyEl) emptyEl.hidden = false;
      });
  }
})();
