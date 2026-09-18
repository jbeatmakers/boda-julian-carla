# Arquitectura de producción

## Fuente de verdad

SQLite vive en el VPS en `/var/lib/boda-julian-carla/wedding.sqlite3`, con WAL y `busy_timeout`. `localStorage` se usa sólo como cola temporal si un RSVP no pudo llegar al servidor.

## Frontend

La invitación es estática:
- principal: GitHub Pages + `boda-julian-carla.bpm.red`;
- fallback: repo Pages separado, sin CNAME, en `jbeatmakers.github.io/boda-julian-carla-pages/`.

Ambas llevan `robots.txt: Disallow /` y meta `noindex`. El fallback acepta RSVP y el acceso administrativo especial igual que la principal.

## Backend/admin

Caddy (contenedor `caddy`) termina TLS y proxyfica `boda-api.13-140-183-198.sslip.io` hacia `boda-wedding:8787` dentro de la red Docker `web`.

`boda-wedding`:
- imagen `python:3.12-alpine`;
- sin puertos publicados;
- `--restart unless-stopped`;
- código/admin montados read-only desde `/opt/boda-julian-carla`;
- SQLite montada read-write desde `/var/lib/boda-julian-carla`;
- secretos sólo por entorno privado del VPS.

## Seguridad

- `BODA` es sólo la puerta social de invitados.
- El código especial de administración se valida en servidor y no se publica en HTML, JavaScript, tests ni documentación.
- La entrada especial emite un token de un solo uso y luego una cookie `HttpOnly; Secure; SameSite=Strict`.
- Las mutaciones admin requieren CSRF.
- Login, entrada especial y RSVP tienen rate limiting.
- Admin/API envían `X-Robots-Tag: noindex`.
- La contraseña administrativa se conserva sólo como PBKDF2.

## RSVP

Cada envío usa `request_id` para idempotencia. Email/teléfono/nombre único pueden enlazar una respuesta con una invitación existente. El servidor vuelve a limitar los lugares según `seats_allowed`; no confía sólo en el selector del navegador.

## Planificador

Sin override manual, la previsión usa lugares confirmados + cupos de invitados/pendientes y luego aplica el margen. Los registros marcados sólo como `possible` se muestran aparte y no inflan comida/bebida hasta convertirse en invitación real.

Stock comprado y aportes recibidos descuentan faltantes; aportes sólo prometidos no cuentan como stock.

## Instagram

El perfil objetivo es `@juli.y.carli`. La tarjeta siempre puede enlazar el perfil; si el OAuth de Meta queda conectado y existen publicaciones, el backend entrega hasta seis piezas al frontend. Tokens/secret nunca se sirven al navegador ni se versionan.

## Backups

El timer systemd de backup permanece fuera del runtime Docker y ejecuta `sqlite3.backup` diariamente. El deploy hace además un backup previo.
