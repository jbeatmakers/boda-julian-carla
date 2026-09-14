# Boda Julián & Carla — producción v2

Sitio y panel para el casamiento del **18 de diciembre de 2026**.

## Qué resuelve esta versión

- Código público de entrada: `BODA` (no es una contraseña administrativa).
- Ceremonia 17:00: Iglesia San Pedro y San Pablo, Carlos Figueroa, San Pablo de Reyes.
- Celebración 18:30: nombre visible neutro `Quincho · San Pablo de Reyes`, con coordenadas exactas del predio.
- Mapas y “Cómo llegar” para ambos puntos.
- Confetti liviano al entrar y al abrir una ubicación; no bloquea la navegación y respeta `prefers-reduced-motion`.
- RSVP persistente en SQLite, compartido entre dispositivos, con cola local de emergencia si el VPS no responde.
- Copia específica para quien no asiste, sin obligación de tarjeta ni regalo.
- Tarjeta para quien asiste + regalo voluntario, sin montos sugeridos.
- Panel real de administración: invitados, precios especiales/sin cargo, pagos, regalos, mesas, gastos, compras, tareas y proveedores.
- Importación del backup del panel anterior y exportación JSON/CSV.
- Backups diarios de SQLite en el VPS, sin depender de GitHub.
- Admin sin contraseña embebida en HTML/JavaScript: PBKDF2 en variable de entorno del VPS.

## Arquitectura

`GitHub` conserva código, historial y opcionalmente dispara deploy. El runtime vive en el VPS:

```text
boda-julian-carla.bpm.red  -> Nginx -> sitio estático
boda-api.bpm.red           -> Nginx -> admin estático + API
                                      -> Python stdlib :8787
                                      -> SQLite WAL
                                      -> backup systemd diario
```

El sitio público conserva una cola local de RSVP y puede ofrecer WhatsApp de respaldo si el API está temporalmente fuera de línea.

## Pruebas

```bash
node --check assets/app.js
node --check assets/admin.js
python3 -m py_compile server/app.py server/backup.py
python3 -m unittest -v tests.test_server tests.test_static
```

## Importante antes de publicar

Los datos bancarios vienen vacíos a propósito para no publicar placeholders. Cargarlos desde el panel cuando correspondan. El precio inicial conservado es `$35.000`, pero se cambia desde `Sitio & tarjeta` sin tocar código.

Ver `docs/DEPLOY.md` y `docs/ARCHITECTURE.md`.
