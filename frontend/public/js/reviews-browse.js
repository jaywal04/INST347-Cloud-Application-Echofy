(function () {
  'use strict';

  var ART_COLORS = ['c1', 'c2', 'c3', 'c4', 'c5', 'c6'];
  var spotifyItems = [];
  var authUserId = null;

  function normReactionEmoji(s) {
    try {
      return String(s || '').normalize('NFC');
    } catch (e) {
      return String(s || '');
    }
  }

  /** Must match server `ALLOWED_REVIEW_REACTION_EMOJIS_ORDERED` (browse picker + sort tie-break). */
  var REACTION_ORDER = [
    '🩷',
    '💯',
    '🫡',
    '❤️‍🔥',
    '👍🏼',
    '👎🏼',
    '💩',
    '🎵',
    '🎶',
    '😂',
    '😍',
    '😡',
    '💀',
    '☠️',
  ];

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

  /** Like control on the right of the reaction row (same row as + and chips). */
  function reviewLikeSlotHtml(r) {
    var n = typeof r.like_count === 'number' ? r.like_count : 0;
    var label = n + ' like' + (n === 1 ? '' : 's');
    var isOwn = authUserId != null && r.user_id === authUserId;
    if (isOwn || authUserId == null) {
      return (
        '<div class="review-like-slot"><span class="review-like-count">' +
        escapeHtml(label) +
        '</span></div>'
      );
    }
    var liked = !!r.liked_by_me;
    return (
      '<div class="review-like-slot">' +
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

  function closeAllReactionPickers() {
    document.querySelectorAll('.review-reaction-picker').forEach(function (p) {
      p.hidden = true;
      p.classList.remove('review-reaction-picker--flip-up');
    });
    document.querySelectorAll('.review-reaction-add').forEach(function (b) {
      b.setAttribute('aria-expanded', 'false');
    });
  }

  function positionReactionPicker(picker) {
    picker.classList.remove('review-reaction-picker--flip-up');
    if (picker.hidden) return;
    requestAnimationFrame(function () {
      if (picker.hidden) return;
      var rect = picker.getBoundingClientRect();
      var margin = 12;
      if (rect.bottom > window.innerHeight - margin) {
        picker.classList.add('review-reaction-picker--flip-up');
      }
    });
  }

  function reviewReactionsRowHtml(r) {
    var counts = r.reaction_counts || {};
    var mineArr = r.my_reactions || [];
    var mine = {};
    mineArr.forEach(function (e) {
      mine[normReactionEmoji(e)] = true;
    });
    /* Preserve API key order = first reaction on this review first (not by count). */
    var chips = Object.keys(counts).filter(function (e) {
      return counts[e] > 0;
    });
    var chipsHtml = chips
      .map(function (em) {
        var c = counts[em];
        var active = mine[normReactionEmoji(em)] ? ' is-mine' : '';
        return (
          '<button type="button" class="review-reaction-chip' +
          active +
          '" data-review-reaction="' +
          String(r.id) +
          '" data-emoji="' +
          em +
          '" aria-label="Reaction ' +
          em +
          ', ' +
          c +
          '">' +
          '<span class="review-reaction-emoji" aria-hidden="true">' +
          em +
          '</span><span class="review-reaction-count">' +
          String(c) +
          '</span></button>'
        );
      })
      .join('');

    var picker = '';
    if (authUserId != null) {
      var grid = REACTION_ORDER.map(function (em) {
        return (
          '<button type="button" class="review-reaction-picker-btn" data-review-reaction-pick="' +
          String(r.id) +
          '" data-emoji="' +
          em +
          '">' +
          em +
          '</button>'
        );
      }).join('');
      picker =
        '<div class="review-reaction-picker-wrap">' +
        '<button type="button" class="review-reaction-add" data-review-reaction-open="' +
        String(r.id) +
        '" aria-expanded="false" aria-haspopup="true" aria-label="Add reaction">+</button>' +
        '<div class="review-reaction-picker" hidden role="menu">' +
        grid +
        '</div></div>';
    }

    return (
      '<div class="review-reaction-row" data-review-id="' +
      String(r.id) +
      '" data-review-user-id="' +
      escapeHtml(String(r.user_id != null ? r.user_id : '')) +
      '">' +
      picker +
      '<div class="review-reaction-chips">' +
      chipsHtml +
      '</div>' +
      reviewLikeSlotHtml(r) +
      '</div>'
    );
  }

  function replaceReactionRow(reviewId, payload) {
    var row = document.querySelector('.review-reaction-row[data-review-id="' + String(reviewId) + '"]');
    if (!row || !payload) return;
    var uidStr = row.getAttribute('data-review-user-id') || '';
    var uid = uidStr === '' ? null : parseInt(uidStr, 10);
    if (isNaN(uid)) uid = null;

    var n = typeof payload.like_count === 'number' ? payload.like_count : null;
    var liked = typeof payload.liked_by_me === 'boolean' ? payload.liked_by_me : null;
    if (n === null) {
      var likeNumEl = row.querySelector('.review-like-num');
      var likeCountEl = row.querySelector('.review-like-slot .review-like-count');
      if (likeNumEl) n = parseInt(likeNumEl.textContent, 10) || 0;
      else if (likeCountEl) {
        var m = (likeCountEl.textContent || '').match(/(\d+)/);
        n = m ? parseInt(m[1], 10) : 0;
      } else n = 0;
    }
    if (liked === null) {
      var lb = row.querySelector('.review-like-btn');
      liked = !!(lb && lb.classList.contains('is-liked'));
    }

    var fake = {
      id: reviewId,
      user_id: uid,
      reaction_counts: payload.reaction_counts || {},
      my_reactions: payload.my_reactions || [],
      like_count: n,
      liked_by_me: liked,
    };
    row.outerHTML = reviewReactionsRowHtml(fake);
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
        reviewReactionsRowHtml(r);

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

  document.addEventListener(
    'click',
    function (ev) {
      if (ev.target.closest('.review-reaction-picker-wrap')) return;
      closeAllReactionPickers();
    },
    true
  );

  var browseList = document.getElementById('reviews-browse-list');
  if (browseList) {
    browseList.addEventListener('click', function (ev) {
      var openBtn = ev.target.closest('[data-review-reaction-open]');
      if (openBtn) {
        ev.preventDefault();
        ev.stopPropagation();
        var wrap = openBtn.closest('.review-reaction-picker-wrap');
        var picker = wrap && wrap.querySelector('.review-reaction-picker');
        if (!picker) return;
        var wasHidden = picker.hidden;
        closeAllReactionPickers();
        picker.hidden = !wasHidden;
        openBtn.setAttribute('aria-expanded', wasHidden ? 'true' : 'false');
        if (!picker.hidden) {
          positionReactionPicker(picker);
        }
        return;
      }

      var pickEm = ev.target.closest('.review-reaction-picker-btn');
      if (pickEm) {
        ev.preventDefault();
        ev.stopPropagation();
        var ridPick = parseInt(pickEm.getAttribute('data-review-reaction-pick'), 10);
        var emPick = normReactionEmoji(pickEm.getAttribute('data-emoji'));
        if (!ridPick || !emPick) return;
        var basePick = apiBase();
        if (!basePick) return;
        var rowPick = pickEm.closest('.review-reaction-row');
        var mineSet = {};
        (rowPick ? rowPick.querySelectorAll('.review-reaction-chip.is-mine') : []).forEach(function (c) {
          var e = c.getAttribute('data-emoji');
          if (e) mineSet[normReactionEmoji(e)] = true;
        });
        var method = mineSet[emPick] ? 'DELETE' : 'POST';
        var urlPick = basePick + '/api/reviews/' + ridPick + '/reactions';
        var reqPick = { method: method, credentials: 'include' };
        if (method === 'DELETE') {
          urlPick += '?' + new URLSearchParams({ emoji: emPick }).toString();
        } else {
          reqPick.headers = { 'Content-Type': 'application/json' };
          reqPick.body = JSON.stringify({ emoji: emPick });
        }
        fetch(urlPick, reqPick)
          .then(function (res) {
            return res.json().then(function (data) {
              return { ok: res.ok, data: data };
            });
          })
          .then(function (_ref) {
            if (!_ref.ok || !_ref.data || !_ref.data.ok) return;
            closeAllReactionPickers();
            replaceReactionRow(ridPick, _ref.data);
          });
        return;
      }

      var chip = ev.target.closest('.review-reaction-chip');
      if (chip && authUserId != null) {
        ev.preventDefault();
        ev.stopPropagation();
        var ridC = parseInt(chip.getAttribute('data-review-reaction'), 10);
        var emC = normReactionEmoji(chip.getAttribute('data-emoji'));
        if (!ridC || !emC) return;
        var baseC = apiBase();
        if (!baseC) return;
        var isMine = chip.classList.contains('is-mine');
        var urlC = baseC + '/api/reviews/' + ridC + '/reactions';
        var reqC = { method: isMine ? 'DELETE' : 'POST', credentials: 'include' };
        if (isMine) {
          urlC += '?' + new URLSearchParams({ emoji: emC }).toString();
        } else {
          reqC.headers = { 'Content-Type': 'application/json' };
          reqC.body = JSON.stringify({ emoji: emC });
        }
        fetch(urlC, reqC)
          .then(function (res) {
            return res.json().then(function (data) {
              return { ok: res.ok, data: data };
            });
          })
          .then(function (_ref) {
            if (!_ref.ok || !_ref.data || !_ref.data.ok) return;
            replaceReactionRow(ridC, _ref.data);
          });
        return;
      }

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
          var slot = btn.closest('.review-like-slot');
          var numEl = slot ? slot.querySelector('.review-like-num') : null;
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
