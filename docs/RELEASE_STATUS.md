# Estado verificable de la release

El identificador público está en `index.html` y el commit desplegado en `/release.json`. El backend informa su SHA-256 normalizado y el estado de lectura de SQLite en `/healthz`. Comparar ambos con la revisión que se está auditando; no asumir vigencia por el nombre de una carpeta.

El pipeline `Validate and publish wedding release` comprueba unidades/integración, Chromium/Firefox/WebKit, igualdad del backend, construcción pública, publicación y verificación posterior. `Wedding production diagnostic` permite repetir comprobaciones públicas sin credenciales SSH y sin escribir invitados.

Los datos y secretos siguen en el VPS; nunca forman parte del artefacto. Los despliegues de backend realizan backup y sólo reinician `boda-wedding`.

El comportamiento y las limitaciones de caché están en `docs/DEPLOY.md` y el mapa operativo está en `docs/HANDOVER.md`. No usar la documentación histórica de la demo localStorage-only.
