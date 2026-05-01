(function () {
  'use strict';

  var API_BASE = window.ECHOFY_API_BASE || '';
  var STORAGE_KEY = 'echofy-discover-shortlist';

  var btn = document.getElementById('btn-spotify-top');
  var statusEl = document.getElementById('spotify-status');
  var resultsEl = document.getElementById('spotify-results');
  var connectLink = document.getElementById('spotify-connect-link');
  var connectedBadge = document.getElementById('spotify-connected-badge');
  var disconnectBtn = document.getElementById('spotify-disconnect-btn');
  var searchForm = document.getElementById('spotify-search-form');
  var searchInput = document.getElementById('spotify-search-input');
  var searchStatusEl = document.getElementById('spotify-search-status');
  var searchResultsEl = document.getElementById('spotify-search-results');
  var searchTypeButtons = document.querySelectorAll('[data-search-type]');
  var surpriseBtn = document.getElementById('btn-surprise');
  var surpriseStatusEl = document.getElementById('spotify-surprise-status');
  var surpriseResultEl = document.getElementById('spotify-surprise-result');
  var shortlistEl = document.getElementById('spotify-shortlist');
  var clearShortlistBtn = document.getElementById('btn-clear-shortlist');

  var fetchOpts = { credentials: 'include' };
  var selectedSearchType = 'track';
  var currentItems = [];
  var itemCache = {};
  var shortlist = loadShortlist();
  var reviews = {};
  var searchPlaceholders = {
    track: 'Search songs...',
    album: 'Search albums...',
    artist: 'Search artists...',
    genre: 'Search genres like afrobeat, house, or indie...',
  };

  if (!btn && !searchForm) return;

  if (connectLink && API_BASE) {
    connectLink.href = API_BASE + '/auth/spotify';
  }

  function updateSpotifyConnectionUi(connected) {
    if (connectLink) connectLink.hidden = !!connected;
    if (connectedBadge) connectedBadge.hidden = !connected;
    if (disconnectBtn) disconnectBtn.hidden = !connected;
  }

  var oauthJustConnected = false;
  try {
    oauthJustConnected = new URLSearchParams(window.location.search).get('spotify') === 'connected';
  } catch (e) {}

  // OAuth success adds ?spotify=connected — show badge even when /api/spotify/session
  // does not see the cookie yet (common on dev: localhost:3001 → localhost:5001 partitioning).
  if (oauthJustConnected) {
    updateSpotifyConnectionUi(true);
  }
  if (oauthJustConnected && statusEl) {
    statusEl.textContent =
      'Spotify connected. Use “Show top Spotify music” for your top tracks (or the chart if none).';
  }
  if (oauthJustConnected && window.history && window.history.replaceState) {
    try {
      var cleanParams = new URLSearchParams(window.location.search);
      cleanParams.delete('spotify');
      var nextPath = window.location.pathname + (cleanParams.toString() ? '?' + cleanParams.toString() : '');
      window.history.replaceState({}, '', nextPath);
    } catch (e2) {}
  }

  if (API_BASE && (connectedBadge || disconnectBtn)) {
    fetch(API_BASE + '/api/spotify/session', fetchOpts)
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (data.connected) {
          updateSpotifyConnectionUi(true);
        } else if (!oauthJustConnected) {
          updateSpotifyConnectionUi(false);
        }
      })
      .catch(function () {});
  }

  if (disconnectBtn && API_BASE) {
    disconnectBtn.addEventListener('click', function () {
      disconnectBtn.disabled = true;
      fetch(API_BASE + '/api/spotify/disconnect', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: '{}',
      })
        .then(function (r) {
          return r.json().then(function (data) {
            return { ok: r.ok, data: data };
          });
        })
        .then(function (ref) {
          if (!ref.ok || !ref.data.ok) {
            if (statusEl) statusEl.textContent = 'Could not disconnect Spotify. Try again.';
            return;
          }
          updateSpotifyConnectionUi(false);
          if (statusEl) {
            statusEl.textContent =
              'Spotify disconnected. You can connect again anytime for personalized top tracks.';
          }
        })
        .catch(function () {
          if (statusEl) statusEl.textContent = 'Network error while disconnecting.';
        })
        .finally(function () {
          disconnectBtn.disabled = false;
        });
    });
  }

  (function showSpotifyOAuthErrorFromUrl() {
    if (!statusEl) return;
    try {
      var params = new URLSearchParams(window.location.search);
      var code = params.get('spotify_error');
      if (!code) return;
      var desc = (params.get('spotify_error_description') || '').trim();
      var human =
        code === 'server_error'
          ? 'Spotify had a temporary problem (server_error). Wait a minute and try Connect Spotify again, or check status.spotify.com.'
          : code === 'access_denied'
            ? 'Spotify login was cancelled.'
            : 'Spotify login did not finish (' + code + ').';
      statusEl.textContent = human + (desc ? ' ' + desc : '');
      if (window.history && window.history.replaceState) {
        params.delete('spotify_error');
        params.delete('spotify_error_description');
        var next = window.location.pathname + (params.toString() ? '?' + params.toString() : '');
        window.history.replaceState({}, '', next);
      }
    } catch (e) {}
  })();

  function loadShortlist() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    } catch (error) {
      return [];
    }
  }

  function saveShortlist() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(shortlist.slice(0, 20)));
  }

  function itemKey(item) {
    return [
      item.type || 'track',
      item.url || '',
      item.name || '',
      (item.artists || []).join(','),
      item.album || '',
    ].join('|');
  }

  function reviewFor(item) {
    return reviews[itemKey(item)];
  }

  function loadReviewsFromBackend() {
    if (!API_BASE) return;

    fetch(API_BASE + '/api/reviews', fetchOpts)
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, status: res.status, data: data };
        });
      })
      .then(function (_ref) {
        if (!_ref.ok) return;
        reviews = {};
        (_ref.data.reviews || []).forEach(function (review) {
          if (review.item_key) reviews[review.item_key] = review;
        });
        refreshReviewSummaries();
      })
      .catch(function (err) {
        console.error('[Echofy] /api/reviews fetch failed', err);
      });
  }

  function saveReviewToBackend(item, rating, text) {
    if (!API_BASE) {
      return Promise.resolve({
        ok: false,
        data: { errors: ['API base URL is not configured for this host.'] },
      });
    }

    return fetch(API_BASE + '/api/reviews', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        item_key: itemKey(item),
        item: item,
        rating: rating,
        text: text,
      }),
    }).then(function (res) {
      return res.json().then(function (data) {
        return { ok: res.ok, status: res.status, data: data };
      });
    });
  }

  function rememberItems(items) {
    items.forEach(function (item) {
      itemCache[itemKey(item)] = item;
    });
  }

  function isSaved(item) {
    var key = itemKey(item);
    return shortlist.some(function (saved) {
      return itemKey(saved) === key;
    });
  }

  function addToShortlist(item) {
    if (isSaved(item)) return false;
    shortlist.unshift(item);
    shortlist = shortlist.slice(0, 20);
    saveShortlist();
    renderShortlist();
    return true;
  }

  function removeFromShortlist(item) {
    var key = itemKey(item);
    shortlist = shortlist.filter(function (saved) {
      return itemKey(saved) !== key;
    });
    saveShortlist();
    renderShortlist();
  }

  function setLoading(loading) {
    if (!btn) return;
    btn.disabled = loading;
    btn.textContent = loading ? 'Loading...' : 'Show top Spotify music';
    btn.setAttribute('aria-busy', loading ? 'true' : 'false');
  }

  function setSearchLoading(loading) {
    if (!searchForm) return;
    var searchBtn = searchForm.querySelector('button[type="submit"]');
    if (searchBtn) {
      searchBtn.disabled = loading;
      searchBtn.textContent = loading ? 'Searching...' : 'Search';
    }
    if (searchInput) searchInput.disabled = loading;
  }

  function sourceLabel(source, data) {
    if (source === 'your_top_tracks') return 'Your top tracks (Spotify)';
    if (source === 'global_top_50') return 'Global Top 50 (Spotify)';
    if (source === 'new_releases') return 'New releases (Spotify)';
    if (source === 'spotify_search') return 'Search results (Spotify)';
    if (source === 'spotify_genre_search') return 'Genre seeds (Spotify)';
    if (source === 'spotify_genre_recommendations' && data && data.genre) {
      return 'Genre pick · ' + prettyGenreName(data.genre);
    }
    if (source === 'spotify_genre_recommendations') return 'Genre pick (Spotify)';
    if (source === 'featured_playlist' && data && data.playlist_name) {
      return 'Featured: ' + data.playlist_name + ' (Spotify)';
    }
    if (source === 'featured_playlist') return 'Featured playlist (Spotify)';
    if (source === 'search_explore') return 'Explore tracks (Spotify search)';
    if (source === 'genre_recommendations') return 'Genre mix (Spotify)';
    return 'Spotify';
  }

  function metaText(item) {
    if (item.type === 'genre') return item.album || 'Genre seed';
    var artists = (item.artists || []).join(', ');
    if (artists && item.album) return artists + ' · ' + item.album;
    return artists || item.album || (item.type ? item.type.charAt(0).toUpperCase() + item.type.slice(1) : 'Spotify');
  }

  function prettyGenreName(name) {
    return String(name || '')
      .split('-')
      .map(function (part) {
        return part ? part.charAt(0).toUpperCase() + part.slice(1) : part;
      })
      .join(' ');
  }

  function createItemRow(item, index, options) {
    var opts = options || {};
    var li = document.createElement('li');
    li.className = 'spotify-track';

    var rank = document.createElement('span');
    rank.className = 'spotify-track-rank';
    rank.textContent = opts.single ? '★' : String(index + 1);

    var art = document.createElement('div');
    art.className = 'spotify-track-art';
    if (item.image) {
      var img = document.createElement('img');
      img.src = item.image;
      img.alt = '';
      img.width = 48;
      img.height = 48;
      art.appendChild(img);
    } else {
      art.textContent = item.type === 'artist' ? 'A' : item.type === 'genre' ? 'G' : '♪';
    }

    var body = document.createElement('div');
    body.className = 'spotify-track-body';

    var title = document.createElement('div');
    title.className = 'spotify-track-name';
    if (item.url) {
      var a = document.createElement('a');
      a.href = item.url;
      a.target = '_blank';
      a.rel = 'noopener noreferrer';
      a.textContent = item.name;
      title.appendChild(a);
    } else {
      title.textContent = item.name;
    }

    var meta = document.createElement('div');
    meta.className = 'spotify-track-meta';
    meta.textContent = metaText(item);

    body.appendChild(title);
    body.appendChild(meta);

    var review = reviewFor(item);
    if (review) {
      body.appendChild(createReviewSummary(review));
    }
    li.appendChild(rank);
    li.appendChild(art);
    li.appendChild(body);

    var actions = document.createElement('div');
    actions.className = 'spotify-track-actions';

    if (item.type === 'genre') {
      var genrePickBtn = document.createElement('button');
      genrePickBtn.type = 'button';
      genrePickBtn.className = 'btn-ghost btn-sm';
      genrePickBtn.textContent = 'Make a pick';
      genrePickBtn.setAttribute('data-genre-pick', item.genre_seed || item.name || '');
      actions.appendChild(genrePickBtn);
    } else {
      var saveBtn = document.createElement('button');
      saveBtn.type = 'button';
      saveBtn.className = 'btn-ghost btn-sm';
      saveBtn.textContent = opts.remove ? 'Remove' : isSaved(item) ? 'Saved' : 'Save';
      saveBtn.setAttribute(opts.remove ? 'data-remove-item' : 'data-save-item', itemKey(item));
      actions.appendChild(saveBtn);

      var reviewBtn = document.createElement('button');
      reviewBtn.type = 'button';
      reviewBtn.className = 'btn-ghost btn-sm';
      reviewBtn.textContent = review ? 'Edit review' : 'Rate / Review';
      reviewBtn.setAttribute('data-review-item', itemKey(item));
      actions.appendChild(reviewBtn);
    }

    if (item.url) {
      var open = document.createElement('a');
      open.className = 'btn-ghost btn-sm';
      open.href = item.url;
      open.target = '_blank';
      open.rel = 'noopener noreferrer';
      open.textContent = 'Open';
      actions.appendChild(open);
    }

    li.appendChild(actions);
    return li;
  }

  function createReviewSummary(review) {
    var summary = document.createElement('div');
    summary.className = 'spotify-review-summary';
    summary.textContent = 'Your rating: ' + review.rating + '/5' + (review.text ? ' - ' + review.text : '');
    return summary;
  }

  function toggleReviewForm(row, item) {
    var existing = row.querySelector('.spotify-review-form');
    if (existing) {
      existing.remove();
      return;
    }

    var review = reviewFor(item) || {};
    var form = document.createElement('form');
    form.className = 'spotify-review-form';
    form.setAttribute('data-review-form', itemKey(item));

    var ratingLabel = document.createElement('label');
    ratingLabel.textContent = 'Rating';
    var rating = document.createElement('select');
    rating.name = 'rating';
    for (var value = 5; value >= 1; value -= 1) {
      var option = document.createElement('option');
      option.value = String(value);
      option.textContent = value + ' star' + (value === 1 ? '' : 's');
      rating.appendChild(option);
    }
    rating.value = String(review.rating || 5);
    ratingLabel.appendChild(rating);

    var reviewLabel = document.createElement('label');
    reviewLabel.textContent = 'Review';
    var text = document.createElement('textarea');
    text.name = 'review';
    text.rows = 3;
    text.maxLength = 280;
    text.placeholder = 'Write a quick note about this song...';
    text.value = review.text || '';
    reviewLabel.appendChild(text);

    var actions = document.createElement('div');
    actions.className = 'spotify-review-actions';

    var save = document.createElement('button');
    save.type = 'submit';
    save.className = 'btn-primary btn-sm';
    save.textContent = 'Save review';

    var cancel = document.createElement('button');
    cancel.type = 'button';
    cancel.className = 'btn-ghost btn-sm';
    cancel.textContent = 'Cancel';
    cancel.addEventListener('click', function () {
      form.remove();
    });

    actions.appendChild(save);
    actions.appendChild(cancel);
    form.appendChild(ratingLabel);
    form.appendChild(reviewLabel);
    form.appendChild(actions);

    form.addEventListener('submit', function (event) {
      event.preventDefault();
      save.disabled = true;
      save.textContent = 'Saving...';

      saveReviewToBackend(item, Number(rating.value), text.value.trim())
        .then(function (_ref) {
          if (!_ref.ok) {
            var message =
              _ref.status === 401
                ? 'Sign in before saving reviews so they can be stored in your account.'
                : apiErrorText(_ref.data, 'Could not save review.');
            if (surpriseStatusEl) surpriseStatusEl.textContent = message;
            return;
          }

          reviews[itemKey(item)] = _ref.data.review;
          updateReviewSummary(row, item);
          form.remove();
          if (surpriseStatusEl) surpriseStatusEl.textContent = 'Review saved to your account.';
        })
        .catch(function (err) {
          console.error('[Echofy] /api/reviews save failed', err);
          if (surpriseStatusEl) surpriseStatusEl.textContent = 'Network error while saving review.';
        })
        .finally(function () {
          save.disabled = false;
          save.textContent = 'Save review';
        });
    });

    row.appendChild(form);
    text.focus();
  }

  function updateReviewSummary(row, item) {
    var body = row.querySelector('.spotify-track-body');
    if (!body) return;
    var existing = body.querySelector('.spotify-review-summary');
    if (existing) existing.remove();
    var review = reviewFor(item);
    if (review) body.appendChild(createReviewSummary(review));

    var reviewBtn = row.querySelector('[data-review-item]');
    if (reviewBtn) reviewBtn.textContent = review ? 'Edit review' : 'Rate / Review';
  }

  function refreshReviewSummaries() {
    document.querySelectorAll('[data-review-item]').forEach(function (button) {
      var key = button.getAttribute('data-review-item');
      var item = itemCache[key];
      var row = button.closest('.spotify-track');
      if (item && row) updateReviewSummary(row, item);
    });
  }

  function renderItems(container, label, items, options) {
    container.innerHTML = '';
    rememberItems(items);

    if (!items.length) {
      var empty = document.createElement('p');
      empty.className = 'spotify-empty';
      empty.textContent = 'No Spotify results to show yet.';
      container.appendChild(empty);
      container.hidden = false;
      return;
    }

    var badge = document.createElement('p');
    badge.className = 'spotify-source-badge';
    badge.textContent = label;

    var list = document.createElement('ul');
    list.className = 'spotify-track-list';

    items.forEach(function (item, index) {
      list.appendChild(createItemRow(item, index, options));
    });

    container.appendChild(badge);
    container.appendChild(list);
    container.hidden = false;
  }

  function apiErrorText(data, fallback) {
    var parts = [];
    if (data && data.message) parts.push(data.message);
    if (data && data.detail) {
      parts.push(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail));
    }
    return parts.join(' — ') || fallback;
  }

  function renderShortlist() {
    if (!shortlistEl) return;
    if (!shortlist.length) {
      shortlistEl.hidden = true;
      shortlistEl.innerHTML = '';
      return;
    }
    renderItems(shortlistEl, 'Your shortlist', shortlist, { remove: true });
  }

  function refreshSaveButtons() {
    document.querySelectorAll('[data-save-item]').forEach(function (button) {
      var key = button.getAttribute('data-save-item');
      var saved = shortlist.some(function (item) {
        return itemKey(item) === key;
      });
      button.textContent = saved ? 'Saved' : 'Save';
    });
  }

  function handleListClick(event) {
    var genrePickBtn = event.target.closest('[data-genre-pick]');
    if (genrePickBtn) {
      var genreSeed = genrePickBtn.getAttribute('data-genre-pick');
      requestGenrePick(genreSeed);
      return;
    }

    var saveBtn = event.target.closest('[data-save-item]');
    if (saveBtn) {
      var saveKey = saveBtn.getAttribute('data-save-item');
      var item = itemCache[saveKey];
      if (item && addToShortlist(item)) {
        saveBtn.textContent = 'Saved';
        if (surpriseStatusEl) surpriseStatusEl.textContent = 'Added to your shortlist.';
      }
      refreshSaveButtons();
      return;
    }

    var removeBtn = event.target.closest('[data-remove-item]');
    if (removeBtn) {
      var removeKey = removeBtn.getAttribute('data-remove-item');
      var saved = shortlist.find(function (candidate) {
        return itemKey(candidate) === removeKey;
      });
      if (saved) removeFromShortlist(saved);
      refreshSaveButtons();
      return;
    }

    var reviewBtn = event.target.closest('[data-review-item]');
    if (reviewBtn) {
      var reviewKey = reviewBtn.getAttribute('data-review-item');
      var reviewItem = itemCache[reviewKey];
      var row = reviewBtn.closest('.spotify-track');
      if (reviewItem && row) toggleReviewForm(row, reviewItem);
    }
  }

  function requestGenrePick(genreSeed) {
    var seed = String(genreSeed || '').trim().toLowerCase();
    if (!seed) {
      if (surpriseStatusEl) surpriseStatusEl.textContent = 'Search for a genre first so I know what mood to use.';
      return;
    }
    if (!API_BASE) {
      if (surpriseStatusEl) surpriseStatusEl.textContent = 'API base URL is not configured for this host.';
      return;
    }

    if (surpriseStatusEl) surpriseStatusEl.textContent = 'Pulling a genre-based recommendation...';
    if (surpriseBtn) {
      surpriseBtn.disabled = true;
      surpriseBtn.textContent = 'Picking...';
    }

    fetch(
      API_BASE + '/api/spotify/recommend-by-genre?genre=' + encodeURIComponent(seed),
      fetchOpts
    )
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, status: res.status, data: data };
        });
      })
      .then(function (_ref) {
        var data = _ref.data;
        if (!_ref.ok) {
          surpriseResultEl.hidden = true;
          surpriseStatusEl.textContent = apiErrorText(data, 'Could not load a genre-based recommendation.');
          return;
        }

        var tracks = data.tracks || [];
        if (!tracks.length) {
          surpriseResultEl.hidden = true;
          surpriseStatusEl.textContent = 'Spotify had no tracks ready for that genre yet.';
          return;
        }

        rememberItems(tracks);
        var pick = tracks[Math.floor(Math.random() * tracks.length)];
        surpriseStatusEl.textContent = 'Pick based on ' + prettyGenreName(data.genre || seed) + '.';
        renderItems(surpriseResultEl, sourceLabel(data.source, data), [pick], { single: true });
        refreshSaveButtons();
      })
      .catch(function (err) {
        console.error('[Echofy] Spotify /api/spotify/recommend-by-genre fetch failed', err);
        surpriseResultEl.hidden = true;
        surpriseStatusEl.textContent = 'Network error while loading a genre pick.';
      })
      .finally(function () {
        if (surpriseBtn) {
          surpriseBtn.disabled = false;
          surpriseBtn.textContent = 'Surprise me';
        }
      });
  }

  function requestSimilarPick(item) {
    if (!item) {
      if (surpriseStatusEl) surpriseStatusEl.textContent = 'Pick a song, album, or artist first.';
      return;
    }
    if (!API_BASE) {
      if (surpriseStatusEl) surpriseStatusEl.textContent = 'API base URL is not configured for this host.';
      return;
    }

    if (surpriseStatusEl) surpriseStatusEl.textContent = 'Finding something in the same lane...';
    if (surpriseBtn) {
      surpriseBtn.disabled = true;
      surpriseBtn.textContent = 'Picking...';
    }

    fetch(API_BASE + '/api/spotify/recommend-like', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(item),
    })
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, status: res.status, data: data };
        });
      })
      .then(function (_ref) {
        var data = _ref.data;
        if (!_ref.ok) {
          surpriseResultEl.hidden = true;
          surpriseStatusEl.textContent = apiErrorText(data, 'Could not load a same-genre recommendation.');
          return;
        }

        var items = data.items || [];
        if (!items.length) {
          surpriseResultEl.hidden = true;
          surpriseStatusEl.textContent = 'Spotify did not return a strong same-genre recommendation yet.';
          return;
        }

        rememberItems(items);
        var pick = items[Math.floor(Math.random() * items.length)];
        var seedName = data.seed_name || item.name || 'your pick';
        surpriseStatusEl.textContent =
          'Because you picked ' + seedName + ', here is another ' + prettyGenreName(data.genre || '') + ' ' + (data.seed_type || item.type || 'pick') + '.';
        renderItems(surpriseResultEl, 'Same-genre pick · ' + prettyGenreName(data.genre || ''), [pick], { single: true });
        refreshSaveButtons();
      })
      .catch(function (err) {
        console.error('[Echofy] Spotify /api/spotify/recommend-like fetch failed', err);
        surpriseResultEl.hidden = true;
        surpriseStatusEl.textContent = 'Network error while loading a same-genre recommendation.';
      })
      .finally(function () {
        if (surpriseBtn) {
          surpriseBtn.disabled = false;
          surpriseBtn.textContent = 'Surprise me';
        }
      });
  }

  if (btn && statusEl && resultsEl) {
    btn.addEventListener('click', function () {
      if (!API_BASE) {
        statusEl.textContent = 'API base URL is not configured for this host. Run the site locally with the Flask backend on port 5001.';
        return;
      }

      setLoading(true);
      statusEl.textContent = '';
      resultsEl.hidden = true;
      resultsEl.innerHTML = '';

      fetch(API_BASE + '/api/spotify/top-tracks', fetchOpts)
        .then(function (res) {
          return res.json().then(function (data) {
            return { ok: res.ok, status: res.status, data: data };
          });
        })
        .then(function (_ref) {
          var ok = _ref.ok;
          var data = _ref.data;

          console.log('[Echofy] Spotify /api/spotify/top-tracks', {
            httpStatus: _ref.status,
            ok: ok,
            payload: data,
            trackCount: data && data.tracks ? data.tracks.length : 0,
          });

          if (!ok) {
            statusEl.textContent = apiErrorText(
              data,
              'Could not load Spotify data. Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in .env and restart the backend.'
            );
            return;
          }

          var tracks = data.tracks || [];
          if (!tracks.length) {
            statusEl.textContent = 'Spotify returned no tracks.';
            return;
          }

          currentItems = tracks;
          statusEl.textContent = data.spotify_session_note || '';
          renderItems(resultsEl, sourceLabel(data.source, data), tracks);
          btn.setAttribute('aria-expanded', 'true');
          refreshSaveButtons();
        })
        .catch(function (err) {
          console.error('[Echofy] Spotify /api/spotify/top-tracks fetch failed', err);
          statusEl.textContent =
            'Network error. Is the backend running on ' + (API_BASE || 'http://localhost:5001') + ' ?';
        })
        .finally(function () {
          setLoading(false);
        });
    });
  }

  searchTypeButtons.forEach(function (typeBtn) {
    typeBtn.addEventListener('click', function () {
      selectedSearchType = typeBtn.getAttribute('data-search-type') || 'track';
      searchTypeButtons.forEach(function (candidate) {
        var active = candidate === typeBtn;
        candidate.classList.toggle('is-active', active);
        candidate.setAttribute('aria-pressed', active ? 'true' : 'false');
      });
      if (searchInput) {
        searchInput.placeholder = searchPlaceholders[selectedSearchType] || searchPlaceholders.track;
        searchInput.focus();
      }
    });
  });

  if (searchForm) {
    searchForm.addEventListener('submit', function (event) {
      event.preventDefault();
      if (!searchStatusEl || !searchResultsEl || !searchInput) return;
      if (!API_BASE) {
        searchStatusEl.textContent = 'API base URL is not configured for this host.';
        return;
      }
      var query = (searchInput.value || '').trim();
      if (query.length < 2) {
        searchStatusEl.textContent = 'Search for at least 2 characters.';
        return;
      }

      setSearchLoading(true);
      searchStatusEl.textContent = '';
      searchResultsEl.hidden = true;
      searchResultsEl.innerHTML = '';

      fetch(
        API_BASE +
          '/api/spotify/search?q=' +
          encodeURIComponent(query) +
          '&type=' +
          encodeURIComponent(selectedSearchType),
        fetchOpts
      )
        .then(function (res) {
          return res.json().then(function (data) {
            return { ok: res.ok, status: res.status, data: data };
          });
        })
        .then(function (_ref) {
          var data = _ref.data;
          if (!_ref.ok) {
            searchStatusEl.textContent = apiErrorText(data, 'Could not search Spotify.');
            return;
          }

          var items = data.items || [];
          currentItems = items;
          searchStatusEl.textContent = items.length
            ? 'Showing ' + items.length + ' ' + selectedSearchType + ' result' + (items.length === 1 ? '.' : 's.')
            : 'No Spotify results found.';
          renderItems(searchResultsEl, sourceLabel(data.source, data) + ' · ' + query, items);
          refreshSaveButtons();
        })
        .catch(function (err) {
          console.error('[Echofy] Spotify /api/spotify/search fetch failed', err);
          searchStatusEl.textContent = 'Network error while searching Spotify.';
        })
        .finally(function () {
          setSearchLoading(false);
        });
    });
  }

  if (surpriseBtn) {
    surpriseBtn.addEventListener('click', function () {
      if (selectedSearchType === 'genre' && currentItems.length && currentItems[0].type === 'genre') {
        var genrePick = currentItems[Math.floor(Math.random() * currentItems.length)];
        requestGenrePick(genrePick.genre_seed || genrePick.name);
        return;
      }

      var pool = currentItems.length ? currentItems : shortlist;
      if (!pool.length) {
        surpriseStatusEl.textContent = 'Load top Spotify music, search Spotify, or search a genre first, then I can pick one.';
        surpriseResultEl.hidden = true;
        return;
      }
      var seedItem = pool[Math.floor(Math.random() * pool.length)];
      requestSimilarPick(seedItem);
    });
  }

  if (clearShortlistBtn) {
    clearShortlistBtn.addEventListener('click', function () {
      shortlist = [];
      saveShortlist();
      renderShortlist();
      refreshSaveButtons();
      surpriseStatusEl.textContent = 'Shortlist cleared.';
    });
  }

  [resultsEl, searchResultsEl, surpriseResultEl, shortlistEl].forEach(function (container) {
    if (container) container.addEventListener('click', handleListClick);
  });

  renderShortlist();
  loadReviewsFromBackend();
})();
