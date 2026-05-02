(function () {
  'use strict';

  var ART_COLORS = ['c1', 'c2', 'c3', 'c4', 'c5', 'c6'];
  var spotifyItems = [];
  var authUserId = null;

  function apiBase() {
    return typeof window.echofyApiBaseUrl === 'function'
      ? window.echofyApiBaseUrl()
      : String(window.ECHOFY_API_BASE || '')
          .trim()
          .replace(/\/+$/, '');
  }

  function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = String(s);
    return d.innerHTML;
  }

  function apiErrorText(data, fallback) {
    var parts = [];
    if (data && data.message) parts.push(data.message);
    if (data && data.detail) {
      parts.push(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail));
    }
    return parts.join(' — ') || fallback;
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

  function typeLabel(t) {
    var x = String(t || 'track').toLowerCase();
    if (x === 'album') return 'Album';
    if (x === 'artist') return 'Artist';
    if (x === 'genre') return 'Genre';
    return 'Track';
  }

  function hideSpotifyBlock() {
    var st = document.getElementById('reviews-spotify-status');
    var sr = document.getElementById('reviews-spotify-results');
    spotifyItems = [];
    if (st) {
      st.textContent = '';
      st.hidden = true;
    }
    if (sr) {
      sr.innerHTML = '';
      sr.hidden = true;
    }
  }

  function hideTrackDetail() {
    var p = document.getElementById('reviews-selected-panel');
    var c = document.getElementById('reviews-for-item-cta');
    if (p) p.hidden = true;
    if (c) c.hidden = true;
  }

  function setToolbarVisible(show) {
    var t = document.querySelector('.reviews-browse-toolbar');
    if (t) t.style.display = show ? '' : 'none';
  }

  function fetchAuth() {
    var base = apiBase();
    if (!base) {
      authUserId = null;
      return Promise.resolve();
    }
    return fetch(base + '/api/auth/me', { credentials: 'include' })
      .then(function (res) {
        return res.json();
      })
      .then(function (data) {
        authUserId =
          data && data.authenticated && data.user && typeof data.user.id === 'number'
            ? data.user.id
            : null;
      })
      .catch(function () {
        authUserId = null;
      });
  }

  function reviewLikeRowHtml(r) {
    var n = typeof r.like_count === 'number' ? r.like_count : 0;
    var label = n + ' like' + (n === 1 ? '' : 's');
    var isOwn = authUserId != null && r.user_id === authUserId;
    if (isOwn || authUserId == null) {
      return (
        '<div class="review-like-row"><span class="review-like-count">' +
        escapeHtml(label) +
        '</span></div>'
      );
    }
    var liked = !!r.liked_by_me;
    return (
      '<div class="review-like-row">' +
      '<button type="button" class="review-like-btn' +
      (liked ? ' is-liked' : '') +
      '" data-review-like="' +
      String(r.id) +
      '" aria-pressed="' +
      (liked ? 'true' : 'false') +
      '" aria-label="' +
      (liked ? 'Unlike' : 'Like') +
      ' this review">' +
      '<span class="review-like-heart" aria-hidden="true">' +
      (liked ? '♥' : '♡') +
      '</span></button>' +
      '<span class="review-like-num">' +
      n +
      '</span>' +
      '</div>'
    );
  }

  function appendReviewCards(list, reviews) {
    if (!list) return;
    (reviews || []).forEach(function (r, idx) {
      var item = r.item || {};
      var initials = (r.username || '?').substring(0, 2).toUpperCase();
      var trackName = item.name || '';
      var artists = (item.artists || []).join(', ');
      var label = trackName + (artists ? ' — ' + artists : '');
      var kind = typeLabel(item.type);

      var artDiv = document.createElement('div');
      artDiv.className = 'review-art';
      if (item.image) {
        artDiv.style.backgroundImage = 'url("' + item.image.replace(/"/g, '%22') + '")';
        artDiv.style.backgroundSize = 'cover';
        artDiv.style.backgroundPosition = 'center';
      } else {
        artDiv.classList.add(ART_COLORS[idx % ART_COLORS.length]);
        artDiv.textContent = kind === 'Genre' ? 'G' : kind === 'Artist' ? 'A' : '♪';
      }

      var bodyDiv = document.createElement('div');
      bodyDiv.className = 'review-body';
      bodyDiv.innerHTML =
        '<div class="review-top">' +
        '<div class="avatar">' +
        escapeHtml(initials) +
        '</div>' +
        '<span class="review-user">' +
        escapeHtml(r.username || '') +
        '</span>' +
        '<span class="review-action">· ' +
        escapeHtml(kind) +
        '</span>' +
        '<span class="review-album-name">' +
        escapeHtml(label) +
        '</span>' +
        '<div class="review-stars">' +
        starsHtml(r.rating) +
        '</div>' +
        '</div>' +
        (r.text ? '<p class="review-text">' + escapeHtml(r.text) + '</p>' : '') +
        '<div class="review-time">' +
        timeAgo(r.updated_at) +
        '</div>' +
        reviewLikeRowHtml(r);

      var card = document.createElement('div');
      card.className = 'review-item';
      card.appendChild(artDiv);
      card.appendChild(bodyDiv);
      list.appendChild(card);
    });
  }

  function renderBrowseList(reviews, q) {
    var list = document.getElementById('reviews-browse-list');
    var emptyEl = document.getElementById('reviews-browse-empty');
    if (!list) return;

    list.innerHTML = '';

    if (emptyEl) {
      emptyEl.textContent = q
        ? 'No reviews match your text search. Try other keywords or use Search Spotify to pick a track.'
        : 'No reviews match these filters yet.';
    }

    if (!reviews || reviews.length === 0) {
      if (emptyEl) emptyEl.hidden = false;
      return;
    }
    if (emptyEl) emptyEl.hidden = true;

    appendReviewCards(list, reviews);
  }

  function renderForItemResult(item, reviews) {
    var list = document.getElementById('reviews-browse-list');
    var emptyBrowse = document.getElementById('reviews-browse-empty');
    var cta = document.getElementById('reviews-for-item-cta');
    var ctaTrack = document.getElementById('reviews-for-item-cta-track');
    if (!list) return;

    list.innerHTML = '';
    if (emptyBrowse) emptyBrowse.hidden = true;

    if (!reviews || reviews.length === 0) {
      if (cta) {
        cta.hidden = false;
        if (ctaTrack) ctaTrack.textContent = item.name || 'this song';
      }
      return;
    }

    if (cta) cta.hidden = true;
    appendReviewCards(list, reviews);
  }

  function updateClearVisibility() {
    var inp = document.getElementById('reviews-search');
    var clr = document.getElementById('reviews-search-clear');
    if (inp && clr) clr.hidden = !inp.value.trim();
  }

  function load() {
    var sortEl = document.getElementById('reviews-sort');
    var catEl = document.getElementById('reviews-category');
    var searchEl = document.getElementById('reviews-search');
    if (!sortEl || !catEl) return;

    hideTrackDetail();
    hideSpotifyBlock();
    setToolbarVisible(true);

    var params = new URLSearchParams();
    params.set('sort', sortEl.value || 'top');
    params.set('category', catEl.value || 'all');
    var q = searchEl ? searchEl.value.trim() : '';
    if (q) params.set('q', q);

    fetch(apiBase() + '/api/reviews/browse?' + params.toString(), { credentials: 'include' })
      .then(function (res) {
        return res.json();
      })
      .then(function (data) {
        updateClearVisibility();
        if (data && data.ok) {
          renderBrowseList(data.reviews, q);
        } else {
          renderBrowseList([], q);
        }
      })
      .catch(function (err) {
        console.error('[Echofy] /api/reviews/browse failed', err);
        updateClearVisibility();
        renderBrowseList([], q);
      });
  }

  function renderSpotifyRows(container, items) {
    container.innerHTML = '';
    var listWrap = document.createElement('div');
    listWrap.className = 'spotify-track-list';
    items.forEach(function (item, index) {
      var row = document.createElement('button');
      row.type = 'button';
      row.className = 'spotify-track reviews-spotify-pick';
      row.setAttribute('data-spotify-index', String(index));

      var art = document.createElement('div');
      art.className = 'spotify-track-art';
      if (item.image) {
        var img = document.createElement('img');
        img.src = item.image;
        img.alt = '';
        art.appendChild(img);
      } else {
        art.textContent = '♪';
      }

      var body = document.createElement('div');
      body.className = 'spotify-track-body';
      var title = document.createElement('div');
      title.className = 'spotify-track-name';
      title.textContent = item.name || 'Track';
      var meta = document.createElement('div');
      meta.className = 'spotify-track-meta';
      var artists = (item.artists || []).join(', ');
      var alb = item.album || '';
      meta.textContent = artists + (alb ? ' · ' + alb : '');

      body.appendChild(title);
      body.appendChild(meta);
      row.appendChild(art);
      row.appendChild(body);
      listWrap.appendChild(row);
    });
    container.appendChild(listWrap);
  }

  function spotifySearch() {
    var searchInp = document.getElementById('reviews-search');
    var st = document.getElementById('reviews-spotify-status');
    var sr = document.getElementById('reviews-spotify-results');
    if (!searchInp || !st || !sr) return;

    var query = (searchInp.value || '').trim();
    if (query.length < 2) {
      st.hidden = false;
      st.textContent = 'Enter at least 2 characters to search Spotify.';
      sr.hidden = true;
      sr.innerHTML = '';
      return;
    }

    var base = apiBase();
    if (!base) {
      st.hidden = false;
      st.textContent = 'API base URL is not configured for this host.';
      return;
    }

    hideTrackDetail();
    setToolbarVisible(true);
    st.hidden = false;
    st.textContent = 'Searching Spotify…';
    sr.hidden = true;
    sr.innerHTML = '';

    fetch(
      base + '/api/spotify/search?q=' + encodeURIComponent(query) + '&type=track',
      { credentials: 'include' }
    )
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, data: data };
        });
      })
      .then(function (_ref) {
        updateClearVisibility();
        var data = _ref.data;
        if (!_ref.ok) {
          st.textContent = apiErrorText(data, 'Could not search Spotify.');
          sr.hidden = true;
          return;
        }
        var items = data.items || [];
        spotifyItems = items;
        var note = data.spotify_session_note ? ' ' + data.spotify_session_note : '';
        st.textContent =
          (items.length
            ? 'Pick the track you mean (' + items.length + ' result' + (items.length === 1 ? '' : 's') + '):'
            : 'No Spotify tracks found for that search.') + note;
        if (!items.length) {
          sr.hidden = true;
          return;
        }
        sr.hidden = false;
        renderSpotifyRows(sr, items);
      })
      .catch(function (err) {
        console.error('[Echofy] Spotify search failed', err);
        st.hidden = false;
        st.textContent = 'Could not reach Spotify search. Try again.';
        sr.hidden = true;
      });
  }

  function pickSpotifyTrack(item) {
    var base = apiBase();
    if (!base) return;

    hideSpotifyBlock();
    setToolbarVisible(false);

    var panel = document.getElementById('reviews-selected-panel');
    var titleEl = document.getElementById('reviews-selected-title');
    var subEl = document.getElementById('reviews-selected-sub');
    if (panel) panel.hidden = false;
    if (titleEl) titleEl.textContent = item.name || 'Track';
    if (subEl) {
      var artists = (item.artists || []).join(', ');
      var alb = item.album || '';
      subEl.textContent = artists + (alb ? ' · ' + alb : '');
    }

    var list = document.getElementById('reviews-browse-list');
    if (list) list.innerHTML = '';

    fetch(base + '/api/reviews/for-item', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ item: item }),
    })
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, data: data };
        });
      })
      .then(function (_ref) {
        if (!_ref.ok) {
          hideTrackDetail();
          setToolbarVisible(true);
          var st = document.getElementById('reviews-spotify-status');
          if (st) {
            st.hidden = false;
            st.textContent = apiErrorText(_ref.data, 'Could not load reviews for this track.');
          }
          return;
        }
        var d = _ref.data;
        var clean = d.item || item;
        renderForItemResult(clean, d.reviews || []);
      })
      .catch(function (err) {
        console.error('[Echofy] /api/reviews/for-item failed', err);
        hideTrackDetail();
        setToolbarVisible(true);
      });
  }

  function textSearch() {
    hideSpotifyBlock();
    hideTrackDetail();
    setToolbarVisible(true);
    load();
  }

  function clearAll() {
    var searchInp = document.getElementById('reviews-search');
    if (searchInp) searchInp.value = '';
    updateClearVisibility();
    hideSpotifyBlock();
    hideTrackDetail();
    setToolbarVisible(true);
    load();
  }

  function backFromTrack() {
    hideTrackDetail();
    setToolbarVisible(true);
    load();
  }

  var sortEl = document.getElementById('reviews-sort');
  var catEl = document.getElementById('reviews-category');
  var searchBtn = document.getElementById('reviews-search-btn');
  var textSearchBtn = document.getElementById('reviews-text-search-btn');
  var searchInp = document.getElementById('reviews-search');
  var searchClr = document.getElementById('reviews-search-clear');
  var spotifyResults = document.getElementById('reviews-spotify-results');
  var backBtn = document.getElementById('reviews-back-from-track');

  if (sortEl) sortEl.addEventListener('change', load);
  if (catEl) catEl.addEventListener('change', load);
  if (searchBtn) searchBtn.addEventListener('click', spotifySearch);
  if (textSearchBtn) textSearchBtn.addEventListener('click', textSearch);
  if (searchClr) searchClr.addEventListener('click', clearAll);
  if (backBtn) backBtn.addEventListener('click', backFromTrack);

  if (searchInp) {
    searchInp.addEventListener('keydown', function (ev) {
      if (ev.key === 'Enter') {
        ev.preventDefault();
        spotifySearch();
      }
    });
    searchInp.addEventListener('input', updateClearVisibility);
  }

  if (spotifyResults) {
    spotifyResults.addEventListener('click', function (ev) {
      var btn = ev.target.closest('[data-spotify-index]');
      if (!btn) return;
      var idx = parseInt(btn.getAttribute('data-spotify-index'), 10);
      if (idx < 0 || idx >= spotifyItems.length) return;
      pickSpotifyTrack(spotifyItems[idx]);
    });
  }

  var browseList = document.getElementById('reviews-browse-list');
  if (browseList) {
    browseList.addEventListener('click', function (ev) {
      var btn = ev.target.closest('.review-like-btn');
      if (!btn) return;
      ev.preventDefault();
      ev.stopPropagation();
      var id = parseInt(btn.getAttribute('data-review-like'), 10);
      if (!id) return;
      var base = apiBase();
      if (!base) return;
      var liked = btn.classList.contains('is-liked');
      var method = liked ? 'DELETE' : 'POST';
      btn.disabled = true;
      fetch(base + '/api/reviews/' + id + '/like', {
        method: method,
        credentials: 'include',
      })
        .then(function (res) {
          return res.json().then(function (data) {
            return { ok: res.ok, data: data };
          });
        })
        .then(function (_ref) {
          btn.disabled = false;
          if (!_ref.ok || !_ref.data || !_ref.data.ok) return;
          var d = _ref.data;
          var cnt = typeof d.like_count === 'number' ? d.like_count : 0;
          var nowLiked = !!d.liked_by_me;
          var row = btn.closest('.review-like-row');
          var numEl = row ? row.querySelector('.review-like-num') : null;
          if (numEl) numEl.textContent = String(cnt);
          btn.classList.toggle('is-liked', nowLiked);
          btn.setAttribute('aria-pressed', nowLiked ? 'true' : 'false');
          btn.setAttribute('aria-label', nowLiked ? 'Unlike this review' : 'Like this review');
          var heart = btn.querySelector('.review-like-heart');
          if (heart) heart.textContent = nowLiked ? '♥' : '♡';
        })
        .catch(function () {
          btn.disabled = false;
        });
    });
  }

  fetchAuth().then(load);
})();
