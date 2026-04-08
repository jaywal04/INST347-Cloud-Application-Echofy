(function () {
  'use strict';

  var raw = window.location.pathname.split('/').pop().replace('.html', '') || '';
  var page = raw || '/';

  var links = [
    { href: 'discover', text: 'Discover' },
    { href: 'friends', text: 'Friends' },
    { href: '#', text: 'Your Echo' },
  ];

  var nav = document.createElement('nav');

  var logo = document.createElement('a');
  logo.className = 'logo';
  logo.href = '/';
  logo.innerHTML = 'Echo<span>fy</span>';

  var ul = document.createElement('ul');
  ul.className = 'nav-links';

  links.forEach(function (link) {
    var li = document.createElement('li');
    var a = document.createElement('a');
    a.href = link.href;
    a.textContent = link.text;
    if (page === link.href) {
      a.className = 'is-active';
    }
    li.appendChild(a);
    ul.appendChild(li);
  });

  // nav-auth sits outside the <ul> so its width changes don't shift the links
  var authDiv = document.createElement('div');
  authDiv.id = 'nav-auth';

  nav.appendChild(logo);
  nav.appendChild(ul);
  nav.appendChild(authDiv);

  var placeholder = document.getElementById('navbar');
  if (placeholder) {
    placeholder.replaceWith(nav);
  }
})();
