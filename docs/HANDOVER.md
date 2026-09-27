# Handover operativo — Boda Julián & Carla

Este documento sustituye la descripción de la demo sin servidor. No usar las copias históricas como fuente de producción.

## Mapa vigente

- Repositorio: `jbeatmakers/boda-julian-carla`.
- Dominio único de la tarjeta: `https://bodajulianycarla.bpm.red/`, con la y.
- API pública: `https://boda-api.bpm.red`.
- Administración: `https://boda-api.13-140-183-198.sslip.io`. Se conserva su origen para no cambiar sesiones ni OAuth.
- VPS: `13.140.183.198`, contenedor `boda-wedding`; proxy `caddy`.
- SQLite persistente: `/var/lib/boda-julian-carla/wedding.sqlite3`.
- Código: `/opt/boda-julian-carla`; entorno privado fuera de Git.
- Pages: artefacto de Actions, no publicación independiente de la raíz del repositorio.

## Qué comprobar antes de trabajar

Leer `docs/DEPLOY.md`, comparar `git status`, la rama, `origin/main`, `/release.json` del sitio y el `code_sha256` de `/healthz`. Conservar cambios de otros hilos. Una release nueva en Git no implica que el backend ya esté desplegado.

BODA abre la tarjeta aunque falle la solicitud de configuración. La interfaz no inventa precio ni datos bancarios mientras espera. El código administrativo sólo se valida en servidor; jamás está embebido como AUTH_PASS en HTML.

Las respuestas se guardan en `rsvp_submissions` y se concilian desde el administrador con la lista de invitados. Las filas pendientes de conciliación no deben confundirse con respuestas perdidas. La cola local es sólo una contingencia, nunca la fuente de verdad.

`js/public-pista.js`, `actualizar.html` y el repositorio retirado `boda-julian-carla-pages` recuperan las entradas antiguas hacia la misma tarjeta. No volver a publicar la demo ni crear un segundo administrador. El dominio sin y no fue demostrado como origen de los fallos reportados.

## Evidencia reproducible

Las suites JavaScript, `python -m unittest discover -s tests -v`, `tests/browser_access.py`, `tools/build_public.py` y `tools/check_production.py` son los controles actuales. Las pruebas de navegador locales usan SQLite temporal; el modo `--base` sólo lee producción. Actions guarda resultados de los tres motores y del navegador contra la URL oficial.

No afirmar que todos los dispositivos del mundo están comprobados: una pestaña congelada que no hace solicitudes no puede recibir código nuevo hasta que se recargue o vuelva a navegar.
