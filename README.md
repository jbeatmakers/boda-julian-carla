# Boda Julián & Carla — producción v3

Sitio, RSVP y wedding planner para el casamiento del **18 de diciembre de 2026**.

## Accesos

- Invitación principal: `https://boda-julian-carla.bpm.red/`
- Fallback independiente: `https://jbeatmakers.github.io/boda-julian-carla-pages/`
- Código de invitados: `BODA`.
- Entrada administrativa: código especial validado exclusivamente por el backend; no se guarda en HTML/JS/Git.
- El fallback se sincroniza desde este repo sin copiar `CNAME`, backend ni secretos.

## Privacidad e indexación

- `robots.txt` bloquea todo rastreo (`Disallow: /`).
- Páginas públicas y admin llevan `robots`, `googlebot` y `bingbot` con `noindex,nofollow,noarchive,nosnippet,noimageindex`.
- El backend añade `X-Robots-Tag` a HTML/JSON.
- Esto evita indexación normal de las páginas, pero el código de acceso sigue siendo la barrera de privacidad; `noindex` no es autenticación.

## Funciones

- RSVP persistente en SQLite y cola local de emergencia.
- Cupos por invitación, confirmados, mesas, dietas y canciones.
- Wedding planner: bebidas, comida, stock, compras, aportes, proveedores, gastos y tareas.
- Editor de textos de la invitación desde el administrador.
- Precios de referencia y lectura de código de barras cuando la fuente está disponible.
- Backups de SQLite en el VPS.

## Arquitectura actual

```text
boda-julian-carla.bpm.red                -> GitHub Pages (sitio público)
jbeatmakers.github.io/...-pages/         -> GitHub Pages fallback sin CNAME
boda-api.13-140-183-198.sslip.io         -> Caddy HTTPS
                                           -> boda-wedding (Docker, red web)
                                           -> Python stdlib :8787
                                           -> SQLite WAL + backups
```

## Instagram

La invitación enlaza siempre `@juli.y.carli`. Si el OAuth de Meta está conectado y hay publicaciones, el mismo bloque muestra automáticamente la galería; si está vacío, no inventa contenido. Los tokens de Meta nunca se exponen al navegador ni se guardan en Git. Ver `docs/INSTAGRAM.md`.

## Pruebas

```bash
node --check assets/app.js
node --check assets/admin.js
python -m py_compile server/app.py server/backup.py
python -m unittest discover -s tests -p 'test_*.py'
```

Los datos bancarios vienen vacíos a propósito. El precio, textos y demás parámetros se administran desde el panel.
