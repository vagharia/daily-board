/* Hand-drawn 24px stroke icon set, injected as an SVG sprite. */
(function () {
  function gear() {
    var teeth = 8, ro = 9.6, ri = 7.4, d = '';
    for (var i = 0; i < teeth * 2; i++) {
      var a0 = (Math.PI * 2 * i) / (teeth * 2) - Math.PI / (teeth * 2) * 0.55;
      var a1 = (Math.PI * 2 * (i + 1)) / (teeth * 2) - Math.PI / (teeth * 2) * 0.55;
      var r = i % 2 === 0 ? ro : ri;
      var p0 = [12 + r * Math.cos(a0), 12 + r * Math.sin(a0)];
      var p1 = [12 + r * Math.cos(a1), 12 + r * Math.sin(a1)];
      d += (i === 0 ? 'M' : 'L') + p0[0].toFixed(2) + ' ' + p0[1].toFixed(2) + 'L' + p1[0].toFixed(2) + ' ' + p1[1].toFixed(2);
    }
    return '<path d="' + d + 'Z"/><circle cx="12" cy="12" r="3"/>';
  }
  var I = {
    gear: gear(),
    refresh: '<path d="M20 12a8 8 0 1 1-2.34-5.66"/><path d="M20 4v5h-5"/>',
    search: '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/>',
    sliders: '<path d="M4 6h16M4 12h16M4 18h16"/><circle cx="9" cy="6" r="2.1" fill="currentColor" stroke="none"/><circle cx="15.5" cy="12" r="2.1" fill="currentColor" stroke="none"/><circle cx="7" cy="18" r="2.1" fill="currentColor" stroke="none"/>',
    x: '<path d="M6 6l12 12M18 6L6 18"/>',
    news: '<path d="M4 5h12v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z"/><path d="M16 9h3a1 1 0 0 1 1 1v9a2 2 0 0 1-2 2h-4"/><path d="M7 9h6M7 13h6M7 17h3"/>',
    radar: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4.8"/><path d="M12 12l6.6-6.6"/><circle cx="15.6" cy="9.2" r="1.2" fill="currentColor" stroke="none"/>',
    quote: '<path d="M4 5h16v11H10l-4.5 3.5V16H4z"/><path d="M9.2 9.2v2.4M13.4 9.2v2.4"/>',
    lock: '<rect x="5" y="11" width="14" height="10" rx="2.2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    crosshair: '<circle cx="12" cy="12" r="7.5"/><path d="M12 2.5v4.2M12 17.3v4.2M2.5 12h4.2M17.3 12h4.2"/><circle cx="12" cy="12" r="1.3" fill="currentColor" stroke="none"/>',
    anchor: '<circle cx="12" cy="5" r="2"/><path d="M12 7v14M5 13c0 4.4 3.1 8 7 8s7-3.6 7-8M8.5 10.5h7M3.5 14.5L5 13l1.5 1.5M17.5 14.5L19 13l1.5 1.5"/>',
    plane: '<path d="M12 2.8c.75 0 1.25.85 1.25 1.85v4.9l7 4.15v1.9l-7-2.15v4.35l2.15 1.65v1.45L12 20.2l-3.4.7v-1.45l2.15-1.65V13.45l-7 2.15v-1.9l7-4.15v-4.9c0-1 .5-1.85 1.25-1.85z"/>',
    planeoff: '<path d="M12 2.8c.75 0 1.25.85 1.25 1.85v4.9l7 4.15v1.9l-7-2.15v4.35l2.15 1.65v1.45L12 20.2l-3.4.7v-1.45l2.15-1.65V13.45l-7 2.15v-1.9l7-4.15v-4.9c0-1 .5-1.85 1.25-1.85z"/><path d="M3.5 3.5l17 17"/>',
    ship: '<path d="M3 15h18l-2.6 4.6H5.6z"/><path d="M7 15V9.5h4V15M11 11.5h6V15M9 9.5V6.2"/>',
    exit: '<path d="M14 4h4a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-4"/><path d="M9.5 16.5L5 12l4.5-4.5M5 12h10"/>',
    hourglass: '<path d="M6 3h12M6 21h12M7 3c0 4.2 5 6 5 9s-5 4.8-5 9M17 3c0 4.2-5 6-5 9s5 4.8 5 9"/>',
    drop: '<path d="M12 3.2s6 6.4 6 10.9a6 6 0 0 1-12 0C6 9.6 12 3.2 12 3.2z"/>',
    gold: '<path d="M3.5 19.5h7.5l1-3.4H4.6zM13 19.5h7.5l-1.1-3.4H12zM8.2 14.2h7.6l-1.1-3.4H9.3z"/>',
    dollar: '<path d="M12 3v18M16.5 7.6c0-1.9-2-3.1-4.5-3.1S7.5 5.7 7.5 7.8c0 4.4 9 2.3 9 6.8 0 2-2 3.4-4.5 3.4s-4.5-1.3-4.5-3.3"/>',
    up: '<path d="M12 6.5l5.5 8.5h-11z" fill="currentColor" stroke="none"/>',
    down: '<path d="M12 17.5l5.5-8.5h-11z" fill="currentColor" stroke="none"/>',
    ext: '<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
    clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.6v.4"/>',
    heart: '<path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/>',
    layers: '<path d="M12 4l9 5-9 5-9-5z"/><path d="M3 14l9 5 9-5"/>',
    play: '<path d="M8 5.2v13.6L19 12z" fill="currentColor" stroke="none"/>',
    check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    pin: '<path d="M12 21s-6.5-6.2-6.5-11a6.5 6.5 0 0 1 13 0c0 4.8-6.5 11-6.5 11z"/><circle cx="12" cy="10" r="2.3"/>',
    sound: '<path d="M4 9.5h3.5L12 6v12l-4.5-3.5H4z"/><path d="M15.5 9a4 4 0 0 1 0 6M18 6.5a7.5 7.5 0 0 1 0 11"/>',
    send: '<path d="M21 3L10.5 13.5M21 3l-6.8 18-3.7-7.5L3 9.8z"/>',
    shield: '<path d="M12 3l7 3v5.2c0 4.9-3.4 8.4-7 9.8-3.6-1.4-7-4.9-7-9.8V6z"/>',
    signal: '<path d="M5 20v-3.5M10 20v-7.5M15 20v-11M20 20V5"/>',
    globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.7 3.8 5.7 3.8 9s-1.3 6.3-3.8 9c-2.5-2.7-3.8-5.7-3.8-9S9.5 5.7 12 3z"/>',
    flame: '<path d="M12 3c1 3.5 5 5.4 5 10a5 5 0 0 1-10 0c0-2.4 1.4-3.8 2.5-5 .3 1.5 1.2 2.4 2.2 2.6C11.2 8.4 11.3 5.6 12 3z"/>',
    alert: '<path d="M12 4l9.2 16H2.8z"/><path d="M12 10v4.4M12 17.2v.3"/>',
    users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c.5-3.5 3.2-5.5 6.5-5.5s6 2 6.5 5.5M16 4.6a3.3 3.3 0 0 1 0 6.4M18.6 14.8c1.7.7 2.8 2.5 3 5.2"/>',
    chev: '<path d="M9 6l6 6-6 6"/>',
    share: '<path d="M12 3v12M7.5 7.5L12 3l4.5 4.5M5 13v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-6"/>',
    sort: '<path d="M7 4v16M3.5 16.5L7 20l3.5-3.5M14 6h7M14 11h5M14 16h3"/>',
    eye: '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    offline: '<path d="M3 3l18 18M8.5 16.5a5 5 0 0 1 7 0M5 12.5a10 10 0 0 1 4-2.3M15 10.2a10 10 0 0 1 4 2.3M12 20h.01"/>',
    tanker: '<path d="M2.5 15.5h19l-2.2 4H4.7z"/><path d="M5 15.5V12h10v3.5M15 13.2h3.6l1.4 2.3M8 12V9.5h3V12"/>',
    image: '<rect x="3.5" y="4.5" width="17" height="15" rx="2.4"/><circle cx="9" cy="10" r="1.8"/><path d="M4 17.5l5-4.5 4 3.5 3-2.5 4.5 4"/>',
    book: '<path d="M12 6.8c-2.6-1.7-5.6-2.1-8.5-1.3v12.9c2.9-.8 5.9-.4 8.5 1.3 2.6-1.7 5.6-2.1 8.5-1.3V5.5c-2.9-.8-5.9-.4-8.5 1.3z"/><path d="M12 6.8v12.9"/>',
    bank: '<path d="M3.5 9.2L12 4.5l8.5 4.7"/><path d="M5.8 10.8v6.2M9.9 10.8v6.2M14.1 10.8v6.2M18.2 10.8v6.2"/><path d="M3.5 19.5h17"/>',
    chip: '<rect x="7" y="7" width="10" height="10" rx="2"/><rect x="10.2" y="10.2" width="3.6" height="3.6" rx=".7"/><path d="M10 3.8V7M14 3.8V7M10 17v3.2M14 17v3.2M3.8 10H7M3.8 14H7M17 10h3.2M17 14h3.2"/>'
  };
  var out = '<svg xmlns="http://www.w3.org/2000/svg" style="display:none">';
  for (var k in I) {
    out += '<symbol id="i-' + k + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' + I[k] + '</symbol>';
  }
  out += '</svg>';
  var holder = document.createElement('div');
  holder.innerHTML = out;
  document.body.insertBefore(holder.firstChild, document.body.firstChild);
})();
