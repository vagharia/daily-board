/* Offline shell + last-known data. */
var SHELL = 'shell-v19';
var DATA = 'data-v1';
var ASSETS = ['./', 'index.html', 'app.css?v=19', 'app.js?v=19', 'icons.js?v=19', 'manifest.webmanifest',
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
  // same-origin: stale-while-revalidate for the shell, fonts and map
  e.respondWith(caches.open(SHELL).then(function (c) {
    return c.match(e.request).then(function (hit) {
      var net = fetch(e.request).then(function (r) { if (r.ok) c.put(e.request, r.clone()); return r; }).catch(function () { return hit; });
      return hit || net;
    });
  }));
});
