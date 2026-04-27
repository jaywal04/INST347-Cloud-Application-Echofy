(function () {
  'use strict';

  var API_BASE = window.ECHOFY_API_BASE || '';
  var route = window.ECHOFY_ROUTE || function (value) { return value; };
  var reviewsEl = document.getElementById('echo-reviews');
  var savedEl = document.getElementById('echo-saved');
  var reviewStatusEl = document.createElement('p');
  var reviewItems = [];

  if (!reviewsEl || !savedEl || !API_BASE) return;

  reviewStatusEl.className = 'echo-feedback';
  reviewStatusEl.hidden = true;
  reviewsEl.parentNode.insertBefore(reviewStatusEl, reviewsEl);

  function fetchJson(path) {
    return fetch(API_BASE + path, { credentials: 'include' }).then(function (res) {
      return res.json().then(function (data) {
        return { ok: res.ok, status: res.status, data: data };
      });
    });
  }

  function stars(rating) {
    var value = Math.max(0, Math.min(5, Number(rating) || 0));
    return '★'.repeat(value) + '☆'.repeat(5 - value);
  }

  function formatDate(value) {
    if (!value) return '';
    var parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return '';
    return parsed.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  }

  function renderReviewEmpty(message) {
    reviewsEl.innerHTML = '<p class="echo-empty">' + message + '</p>';
  }

  function renderSavedEmpty(message) {
    savedEl.innerHTML = '<p class="echo-empty">' + message + '</p>';
    savedEl.hidden = false;
  }

  function renderReviews(reviews) {
    reviewItems = (reviews || []).slice();
    if (!reviews.length) {
      renderReviewEmpty('You have not written any reviews yet. Rate a track on Discover and it will show up here.');
      return;
    }

    reviewsEl.innerHTML = '';
    reviews.forEach(function (review) {
      var card = document.createElement('article');
      card.className = 'echo-review-card';

      var top = document.createElement('div');
      top.className = 'echo-review-top';

      var name = document.createElement('h3');
      name.className = 'echo-review-title';
      name.textContent = review.item && review.item.name ? review.item.name : 'Untitled track';

      var rating = document.createElement('div');
      rating.className = 'echo-review-rating';
      rating.textContent = stars(review.rating);

      top.appendChild(name);
      top.appendChild(rating);

      var meta = document.createElement('p');
      meta.className = 'echo-review-meta';
      var artists = review.item && review.item.artists ? review.item.artists.join(', ') : '';
      var album = review.item && review.item.album ? review.item.album : '';
      meta.textContent = artists && album ? artists + ' · ' + album : artists || album || 'Spotify';

      var body = document.createElement('p');
      body.className = 'echo-review-text';
      body.textContent = review.text || 'Rated without a written note.';

      var date = document.createElement('p');
      date.className = 'echo-review-date';
      date.textContent = formatDate(review.updated_at);

      var actions = document.createElement('div');
      actions.className = 'echo-review-actions';

      var remove = document.createElement('button');
      remove.type = 'button';
      remove.className = 'btn-ghost btn-sm echo-review-delete';
      remove.textContent = 'Delete rating';
      remove.setAttribute('data-delete-review', review.item_key || '');

      actions.appendChild(remove);

      card.appendChild(top);
      card.appendChild(meta);
      card.appendChild(body);
      card.appendChild(date);
      card.appendChild(actions);
      reviewsEl.appendChild(card);
    });
  }

  function setReviewStatus(message, isError) {
    if (!message) {
      reviewStatusEl.hidden = true;
      reviewStatusEl.textContent = '';
      reviewStatusEl.classList.remove('is-error');
      return;
    }

    reviewStatusEl.hidden = false;
    reviewStatusEl.textContent = message;
    reviewStatusEl.classList.toggle('is-error', !!isError);
  }

  function deleteReview(itemKeyValue) {
    return fetch(API_BASE + '/api/reviews', {
      method: 'DELETE',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ item_key: itemKeyValue }),
    }).then(function (res) {
      return res.json().then(function (data) {
        return { ok: res.ok, status: res.status, data: data };
      });
    });
  }

  function renderSaved(items) {
    if (!items.length) {
      renderSavedEmpty('You have not saved any songs yet. Use Save on Discover and they will land here.');
      return;
    }

    savedEl.innerHTML = '';
    savedEl.hidden = false;

    var list = document.createElement('ul');
    list.className = 'spotify-track-list';

    items.forEach(function (entry, index) {
      var item = entry.item || {};
      var row = document.createElement('li');
      row.className = 'spotify-track';

      var rank = document.createElement('span');
      rank.className = 'spotify-track-rank';
      rank.textContent = String(index + 1);

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
        art.textContent = '♪';
      }

      var body = document.createElement('div');
      body.className = 'spotify-track-body';

      var title = document.createElement('div');
      title.className = 'spotify-track-name';
      if (item.url) {
        var link = document.createElement('a');
        link.href = item.url;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.textContent = item.name || 'Untitled track';
        title.appendChild(link);
      } else {
        title.textContent = item.name || 'Untitled track';
      }

      var meta = document.createElement('div');
      meta.className = 'spotify-track-meta';
      var artists = item.artists || [];
      meta.textContent = artists.join(', ') + (item.album ? ' · ' + item.album : '');

      var savedAt = document.createElement('div');
      savedAt.className = 'echo-saved-date';
      savedAt.textContent = entry.saved_at ? 'Saved ' + formatDate(entry.saved_at) : '';

      body.appendChild(title);
      body.appendChild(meta);
      body.appendChild(savedAt);

      row.appendChild(rank);
      row.appendChild(art);
      row.appendChild(body);
      list.appendChild(row);
    });

    savedEl.appendChild(list);
  }

  Promise.all([
    fetchJson('/api/auth/me'),
    fetchJson('/api/reviews'),
    fetchJson('/api/reviews/saved'),
  ])
    .then(function (results) {
      var auth = results[0];
      var reviewRes = results[1];
      var savedRes = results[2];

      if (!auth.ok || !auth.data.authenticated) {
        window.location.href = route('login');
        return;
      }

      renderReviews(reviewRes.ok ? (reviewRes.data.reviews || []) : []);
      renderSaved(savedRes.ok ? (savedRes.data.items || []) : []);
    })
    .catch(function () {
      renderReviewEmpty('Could not load your recent reviews right now.');
      renderSavedEmpty('Could not load your saved songs right now.');
    });

  reviewsEl.addEventListener('click', function (event) {
    var button = event.target.closest('[data-delete-review]');
    if (!button) return;

    var itemKeyValue = button.getAttribute('data-delete-review') || '';
    if (!itemKeyValue) return;

    setReviewStatus('');
    button.disabled = true;
    button.textContent = 'Deleting...';

    deleteReview(itemKeyValue)
      .then(function (_ref) {
        if (!_ref.ok) {
          var message =
            _ref.status === 401
              ? 'Sign in again before editing reviews in Your Echo.'
              : ((_ref.data && _ref.data.errors && _ref.data.errors[0]) || 'Could not delete this rating right now.');
          setReviewStatus(message, true);
          return;
        }

        reviewItems = reviewItems.filter(function (review) {
          return review.item_key !== itemKeyValue;
        });
        renderReviews(reviewItems);
        setReviewStatus('Rating removed from Your Echo.');
      })
      .catch(function () {
        setReviewStatus('Network error while deleting this rating.', true);
      })
      .finally(function () {
        if (document.body.contains(button)) {
          button.disabled = false;
          button.textContent = 'Delete rating';
        }
      });
  });
})();
