# Arquitectura de producción

## Decisión principal

No usar `localStorage` como base de datos. Solo se usa como cola temporal de emergencia para un RSVP que no pudo llegar al servidor.

### Fuente de verdad

SQLite en el VPS (`/var/lib/boda-julian-carla/wedding.sqlite3`) con WAL y `busy_timeout`.

### GitHub

GitHub sirve para:

- versionado y auditoría;
- conservar el código;
- opcionalmente disparar un deploy con runner self-hosted.

GitHub **no es** la base de datos y no participa en cada confirmación, edición o consulta del admin.

## Seguridad

- El código `18DIC` es una puerta social para invitados; no se considera secreto.
- La contraseña administrativa no existe en el repositorio.
- Hash PBKDF2-SHA256 con salt e iteraciones altas en `/etc/boda-julian-carla.env`.
- Sesión mediante cookie `HttpOnly; Secure; SameSite=Strict`.
- Mutaciones del panel requieren token CSRF adicional.
- Rate limiting básico para login y RSVP.
- El servicio corre con usuario sin login y hardening de systemd.
- El backend escucha solo en `127.0.0.1`; Nginx es el único frente público.

## Consistencia de RSVP

Cada envío genera un `request_id` único. Si el navegador reintenta por una caída de red, el servidor reconoce el mismo ID y no duplica la confirmación.

Si teléfono o email coincide con un invitado ya cargado, se actualiza ese invitado en vez de insertar uno nuevo.

## Backups

Timer de systemd diario. Usa la API `sqlite3.backup`, por lo que obtiene una copia coherente incluso con la base activa. Retención inicial: 45 días.
