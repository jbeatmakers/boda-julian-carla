// Recovery shim for invitation HTML cached before the BODA release.
(() => {
  "use strict";
  const current = document.querySelector('meta[name="wedding-release"]')?.content;
  if (current) return;
  const target = new URL("https://bodajulianycarla.bpm.red/actualizar.html");
  target.searchParams.set("legacy", "1");
  target.searchParams.set("_refresh", String(Date.now()));
  target.hash = window.location.hash;
  window.location.replace(target.href);
})();
