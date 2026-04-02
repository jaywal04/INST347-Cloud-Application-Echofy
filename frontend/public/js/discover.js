(function () {
  'use strict';

  var host = window.location.hostname;
  var API_BASE =
    host === 'localhost' || host === '127.0.0.1' ? 'http://127.0.0.1:5000' : '';

  var btn = document.getElementById('btn-spotify-top');
  var statusEl = document.getElementById('spotify-status');
  var resultsEl = document.getElementById('spotify-results');

  if (!btn || !statusEl || !resultsEl) return;

  function setLoading(loading) {
    btn.disabled = loading;
    btn.textContent = loading ? 'Loading…' : 'Show top Spotify music';
    btn.setAttribute('aria-busy', loading ? 'true' : 'false');
  }

  function sourceLabel(source) {
    if (source === 'your_top_tracks') return 'Your top tracks (Spotify)';
    if (source === 'global_top_50') return 'Global Top 50 (Spotify)';
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

    fetch(API_BASE + '/api/spotify/top-tracks')
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, status: res.status, data: data };
        });
      })
      .then(function (_ref) {
        var ok = _ref.ok;
        var data = _ref.data;

        if (!ok) {
          statusEl.textContent =
            data.message || data.detail || 'Could not load Spotify data. Check JAY_SPOTIFY_TOKEN and that the backend is running.';
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
        badge.textContent = sourceLabel(data.source);

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
      .catch(function () {
        statusEl.textContent = 'Network error. Is the backend running on http://127.0.0.1:5000 ?';
      })
      .finally(function () {
        setLoading(false);
      });
  });
})();
