// Send retired cached HTML to the current invitation, never accept retired codes.
(function () {
  "use strict";
  var marker = document.querySelector('meta[name="wedding-release"]');
  if (marker && marker.content) return;
  window.location.replace("https://bodajulianycarla.bpm.red/actualizar.html?legacy=1&_refresh=" + new Date().getTime() + window.location.hash);
}());
