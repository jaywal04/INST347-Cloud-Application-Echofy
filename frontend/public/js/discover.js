(function () {
  'use strict';

  var host = window.location.hostname;
  var API_BASE =
    host === 'localhost' || host === '127.0.0.1' ? 'http://127.0.0.1:5000' : '';

  var btn = document.getElementById('btn-spotify-top');
  var statusEl = document.getElementById('spotify-status');
  var resultsEl = document.getElementById('spotify-results');
  var connectLink = document.getElementById('spotify-connect-link');
  var connectedBadge = document.getElementById('spotify-connected-badge');

  var fetchOpts = { credentials: 'include' };

  if (!btn || !statusEl || !resultsEl) return;

  if (connectLink && API_BASE) {
    connectLink.href = API_BASE + '/auth/spotify';
  }

  if (API_BASE && connectedBadge) {
    fetch(API_BASE + '/api/spotify/session', fetchOpts)
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        if (data.connected) {
          connectedBadge.hidden = false;
        }
      })
      .catch(function () {});
  }

  if (window.location.search.indexOf('spotify=connected') !== -1 && statusEl) {
    statusEl.textContent =
      'Spotify connected. Use “Show top Spotify music” for your top tracks (or the chart if none).';
  }

  function setLoading(loading) {
    btn.disabled = loading;
    btn.textContent = loading ? 'Loading…' : 'Show top Spotify music';
    btn.setAttribute('aria-busy', loading ? 'true' : 'false');
  }

  function sourceLabel(source, data) {
    if (source === 'your_top_tracks') return 'Your top tracks (Spotify)';
    if (source === 'global_top_50') return 'Global Top 50 (Spotify)';
    if (source === 'new_releases') return 'New releases (Spotify)';
    if (source === 'featured_playlist' && data && data.playlist_name) {
      return 'Featured: ' + data.playlist_name + ' (Spotify)';
    }
    if (source === 'featured_playlist') return 'Featured playlist (Spotify)';
    return 'Spotify';
  }

  btn.addEventListener('click', function () {
    if (!API_BASE) {
      statusEl.textContent = 'API base URL is not configured for this host. Run the site locally with the Flask backend on port 5000.';
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
          var parts = [];
          if (data.message) parts.push(data.message);
          if (data.detail) {
            parts.push(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail));
          }
          statusEl.textContent =
            parts.join(' — ') ||
            'Could not load Spotify data. Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in .env and restart the backend.';
          return;
        }

        var tracks = data.tracks || [];
        if (!tracks.length) {
          statusEl.textContent = 'Spotify returned no tracks.';
          return;
        }

        statusEl.textContent = '';
        var badge = document.createElement('p');
        badge.className = 'spotify-source-badge';
        badge.textContent = sourceLabel(data.source, data);

        var list = document.createElement('ul');
        list.className = 'spotify-track-list';

        tracks.forEach(function (t, i) {
          var li = document.createElement('li');
          li.className = 'spotify-track';

          var rank = document.createElement('span');
          rank.className = 'spotify-track-rank';
          rank.textContent = String(i + 1);

          var art = document.createElement('div');
          art.className = 'spotify-track-art';
          if (t.image) {
            var img = document.createElement('img');
            img.src = t.image;
            img.alt = '';
            img.width = 48;
            img.height = 48;
            art.appendChild(img);
          } else {
            art.textContent = '♪';
          }

          var body = document.createElement('div');
          body.className = 'spotify-track-body';

          var title = document.createElement('div');
          title.className = 'spotify-track-name';
          if (t.url) {
            var a = document.createElement('a');
            a.href = t.url;
            a.target = '_blank';
            a.rel = 'noopener noreferrer';
            a.textContent = t.name;
            title.appendChild(a);
          } else {
            title.textContent = t.name;
          }

          var meta = document.createElement('div');
          meta.className = 'spotify-track-meta';
          meta.textContent = (t.artists || []).join(', ') + (t.album ? ' · ' + t.album : '');

          body.appendChild(title);
          body.appendChild(meta);
          li.appendChild(rank);
          li.appendChild(art);
          li.appendChild(body);
          list.appendChild(li);
        });

        resultsEl.appendChild(badge);
        resultsEl.appendChild(list);
        resultsEl.hidden = false;
        btn.setAttribute('aria-expanded', 'true');
      })
      .catch(function (err) {
        console.error('[Echofy] Spotify /api/spotify/top-tracks fetch failed', err);
        statusEl.textContent = 'Network error. Is the backend running on http://127.0.0.1:5000 ?';
      })
      .finally(function () {
        setLoading(false);
      });
  });
})();
