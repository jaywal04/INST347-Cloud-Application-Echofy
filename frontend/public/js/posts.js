(function () {
  'use strict';

  var API_BASE = window.ECHOFY_API_BASE || '';
  var listEl = document.getElementById('posts-list');
  var emptyEl = document.getElementById('posts-empty');
  var statusEl = document.getElementById('posts-status');
  var ctaDiscover = document.getElementById('posts-cta-discover');

  function apiBase() {
    return typeof window.echofyApiBaseUrl === 'function'
      ? window.echofyApiBaseUrl()
      : String(API_BASE).trim().replace(/\/+$/, '');
  }

  function setStatus(msg, isError) {
    if (!statusEl) return;
    if (!msg) {
      statusEl.hidden = true;
      statusEl.textContent = '';
      return;
    }
    statusEl.hidden = false;
    statusEl.textContent = msg;
    statusEl.classList.toggle('posts-manage-status--error', !!isError);
  }

  function discoverHref() {
    if (typeof window.echofyUserPath === 'function') {
      try {
        return window.echofyUserPath('discovery');
      } catch (e) {}
    }
    return '/discover';
  }

  if (ctaDiscover) {
    ctaDiscover.setAttribute('href', discoverHref());
  }

  function apiErrorText(data, fallback) {
    if (data && data.errors && data.errors.length) return data.errors.join(' ');
    return fallback || 'Request failed.';
  }

  function buildRatingSelect(value) {
    var sel = document.createElement('select');
    sel.className = 'posts-manage-rating';
    sel.setAttribute('aria-label', 'Star rating');
    for (var v = 5; v >= 1; v -= 1) {
      var opt = document.createElement('option');
      opt.value = String(v);
      opt.textContent = v + (v === 1 ? ' star' : ' stars');
      sel.appendChild(opt);
    }
    sel.value = String(Math.min(5, Math.max(1, parseInt(value, 10) || 5)));
    return sel;
  }

  function renderCard(review) {
    var item = review.item || {};
    var artists = Array.isArray(item.artists) ? item.artists.join(', ') : '';
    var label = (item.name || 'Unknown') + (artists ? ' — ' + artists : '');
    var type = (item.type || 'track').replace(/^./, function (c) {
      return c.toUpperCase();
    });

    var section = document.createElement('section');
    section.className = 'discover-panel post-manage-card';
    section.setAttribute('data-review-id', String(review.id));

    var head = document.createElement('div');
    head.className = 'post-manage-card-head';

    var art = document.createElement('div');
    art.className = 'post-manage-art';
    if (item.image) {
      art.style.backgroundImage = 'url("' + String(item.image).replace(/"/g, '%22') + '")';
      art.style.backgroundSize = 'cover';
      art.style.backgroundPosition = 'center';
    } else {
      art.classList.add('post-manage-art--placeholder');
      art.textContent = '♪';
    }

    var meta = document.createElement('div');
    meta.className = 'post-manage-meta';
    var h = document.createElement('h2');
    h.className = 'post-manage-title';
    h.textContent = label;
    var sub = document.createElement('p');
    sub.className = 'post-manage-sub';
    sub.textContent = type + (item.album ? ' · ' + item.album : '');
    meta.appendChild(h);
    meta.appendChild(sub);

    head.appendChild(art);
    head.appendChild(meta);

    var row = document.createElement('div');
    row.className = 'post-manage-fields';

    var ratingWrap = document.createElement('div');
    ratingWrap.className = 'form-group';
    var ratingLabel = document.createElement('label');
    ratingLabel.textContent = 'Rating';
    ratingLabel.setAttribute('for', 'posts-rating-' + review.id);
    var ratingSel = buildRatingSelect(review.rating);
    ratingSel.id = 'posts-rating-' + review.id;
    ratingWrap.appendChild(ratingLabel);
    ratingWrap.appendChild(ratingSel);

    var textWrap = document.createElement('div');
    textWrap.className = 'form-group';
    var textLabel = document.createElement('label');
    textLabel.textContent = 'Review';
    textLabel.setAttribute('for', 'posts-text-' + review.id);
    var ta = document.createElement('textarea');
    ta.id = 'posts-text-' + review.id;
    ta.className = 'posts-manage-textarea';
    ta.rows = 3;
    ta.maxLength = 280;
    ta.value = review.text || '';
    textWrap.appendChild(textLabel);
    textWrap.appendChild(ta);

    row.appendChild(ratingWrap);
    row.appendChild(textWrap);

    var actions = document.createElement('div');
    actions.className = 'post-manage-actions';

    var saveBtn = document.createElement('button');
    saveBtn.type = 'button';
    saveBtn.className = 'btn-primary btn-sm';
    saveBtn.textContent = 'Save changes';

    var delBtn = document.createElement('button');
    delBtn.type = 'button';
    delBtn.className = 'btn-ghost btn-sm post-manage-delete';
    delBtn.textContent = 'Delete';

    actions.appendChild(saveBtn);
    actions.appendChild(delBtn);

    section.appendChild(head);
    section.appendChild(row);
    section.appendChild(actions);

    saveBtn.addEventListener('click', function () {
      var base = apiBase();
      if (!base) {
        setStatus('API is not configured for this host.', true);
        return;
      }
      saveBtn.disabled = true;
      saveBtn.textContent = 'Saving…';
      setStatus('');
      fetch(base + '/api/reviews', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          item_key: review.item_key,
          item: item,
          rating: parseInt(ratingSel.value, 10),
          text: ta.value.trim(),
        }),
      })
        .then(function (res) {
          return res.json().then(function (data) {
            return { ok: res.ok, data: data };
          });
        })
        .then(function (_ref) {
          if (!_ref.ok || !_ref.data || !_ref.data.ok) {
            setStatus(apiErrorText(_ref.data, 'Could not save.'), true);
            return;
          }
          setStatus('Saved.');
          if (_ref.data.review) {
            review.rating = _ref.data.review.rating;
            review.text = _ref.data.review.text || '';
            ta.value = review.text;
            ratingSel.value = String(review.rating);
          }
        })
        .catch(function () {
          setStatus('Network error. Try again.', true);
        })
        .finally(function () {
          saveBtn.disabled = false;
          saveBtn.textContent = 'Save changes';
        });
    });

    delBtn.addEventListener('click', function () {
      if (!window.confirm('Delete this review permanently?')) return;
      var base = apiBase();
      if (!base) {
        setStatus('API is not configured for this host.', true);
        return;
      }
      delBtn.disabled = true;
      saveBtn.disabled = true;
      setStatus('');
      fetch(base + '/api/reviews/' + encodeURIComponent(String(review.id)), {
        method: 'DELETE',
        credentials: 'include',
      })
        .then(function (res) {
          return res.json().then(function (data) {
            return { ok: res.ok, data: data };
          });
        })
        .then(function (_ref) {
          if (!_ref.ok || !_ref.data || !_ref.data.ok) {
            setStatus(apiErrorText(_ref.data, 'Could not delete.'), true);
            delBtn.disabled = false;
            saveBtn.disabled = false;
            return;
          }
          section.remove();
          setStatus('Review deleted.');
          if (listEl && listEl.children.length === 0 && emptyEl) {
            emptyEl.hidden = false;
          }
        })
        .catch(function () {
          setStatus('Network error. Try again.', true);
          delBtn.disabled = false;
          saveBtn.disabled = false;
        });
    });

    return section;
  }

  function load() {
    var base = apiBase();
    if (!base) {
      setStatus('API is not configured.', true);
      return;
    }
    setStatus('Loading…');
    if (listEl) listEl.innerHTML = '';
    fetch(base + '/api/reviews', { credentials: 'include' })
      .then(function (res) {
        if (res.status === 401) {
          window.location.href = '/login';
          return null;
        }
        return res.json();
      })
      .then(function (data) {
        if (!data) return;
        setStatus('');
        if (!data.ok || !Array.isArray(data.reviews)) {
          setStatus(apiErrorText(data, 'Could not load reviews.'), true);
          return;
        }
        if (!listEl) return;
        if (data.reviews.length === 0) {
          if (emptyEl) emptyEl.hidden = false;
          return;
        }
        if (emptyEl) emptyEl.hidden = true;
        data.reviews.forEach(function (r) {
          listEl.appendChild(renderCard(r));
        });
      })
      .catch(function () {
        setStatus('Network error. Try again.', true);
      });
  }

  load();
})();
