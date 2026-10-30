/* Offline shell + last-known data. */
var SHELL = 'shell-v30';
var DATA = 'data-v1';
var ASSETS = ['./', 'index.html', 'app.css?v=30', 'app.js?v=30', 'icons.js?v=30', 'manifest.webmanifest',
  'icons/icon-192.png', 'icons/apple-touch-icon.png'];
self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(SHELL).then(function (c) { return c.addAll(ASSETS); }).then(function () { return self.skipWaiting(); }));
});
self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) { return k !== SHELL && k !== DATA; }).map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});
self.addEventListener('fetch', function (e) {
  var url = new URL(e.request.url);
  if (e.request.method !== 'GET') return;
  // generated data: network first, fall back to the last copy
  if (url.hostname === 'raw.githubusercontent.com' && /\/data\//.test(url.pathname)) {
    var key = url.origin + url.pathname;
    e.respondWith(fetch(e.request).then(function (r) {
      if (r.ok) { var copy = r.clone(); caches.open(DATA).then(function (c) { c.put(key, copy); }); }
      return r;
    }).catch(function () { return caches.open(DATA).then(function (c) { return c.match(key); }); }));
    return;
  }
  if (url.origin !== location.origin) return;
  if (/release\.json$/.test(url.pathname)) return;      // always from the network: it announces updates
  // the page itself: from the network first, so a new version shows the next time the app opens (iPhone home-screen
  // apps are resumed, not restarted, and kept the old page for days); the saved copy after 3 seconds or offline.
  // The request revalidates: an unchanged page costs a few hundred bytes ("not modified")
  if (e.request.mode === 'navigate' || /\/(index\.html)?$/.test(url.pathname)) {
    var page = url.origin + url.pathname.replace(/index\.html$/, '');     // one saved copy, whatever the query
    e.respondWith(caches.open(SHELL).then(function (c) {
      var net = fetch(e.request, { cache: 'no-cache' }).then(function (r) {
        if (r.ok) c.put(page, r.clone());
        return r;
      });
      var saved = c.match(page).then(function (hit) { return hit || c.match('index.html'); });
      var late = new Promise(function (res) { setTimeout(function () { saved.then(function (h) { if (h) res(h); }); }, 3000); });
      return Promise.race([net.catch(function () { return saved; }), late]).then(function (r) { return r || net; });
    }));
    return;
  }
  // same-origin: stale-while-revalidate for the scripts, styles, fonts and map (their addresses carry the version)
  e.respondWith(caches.open(SHELL).then(function (c) {
    return c.match(e.request).then(function (hit) {
      var net = fetch(e.request).then(function (r) { if (r.ok) c.put(e.request, r.clone()); return r; }).catch(function () { return hit; });
      return hit || net;
    });
  }));
});
