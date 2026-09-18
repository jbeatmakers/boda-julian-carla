# Deploy actual de la boda

## Producción

- Invitación principal: `https://boda-julian-carla.bpm.red/` (GitHub Pages).
- Respaldo independiente: `https://jbeatmakers.github.io/boda-julian-carla-pages/`.
- Admin/API: `https://boda-api.13-140-183-198.sslip.io/`.
- Runtime: contenedor Docker `boda-wedding` en la red privada `web`.
- Proxy/TLS: Caddy existente del VPS.
- Datos: `/var/lib/boda-julian-carla/wedding.sqlite3`.
- Entorno privado: `/etc/boda-julian-carla.env`.

GitHub no participa en RSVP, admin ni SQLite. Una caída de GitHub no afecta el backend; la URL Pages alternativa cubre el frontend.

## Actualizar código

En el VPS, el helper actual copia sólo backend/admin, hace backup, reinicia únicamente `boda-wedding`, verifica salud desde Caddy y revierte código si falla:

```bash
sudo /usr/local/sbin/deploy-boda-julian-carla /ruta/al/checkout
```

El frontend público se publica con GitHub Pages al hacer push a `main`. El repo espejo sincroniza sólo los archivos públicos y nunca copia CNAME, backend ni secretos.

## Cambiar variables privadas

Editar `/etc/boda-julian-carla.env` y luego **recrear** el contenedor; un simple `docker restart` no recarga variables:

```bash
sudo /usr/local/sbin/recreate-boda-wedding
```

Para cambiar usuario/contraseña administrativa puede usarse `deploy/configure-admin.sh`, que guarda sólo PBKDF2 y recrea el contenedor.

## Caddy

El bloque canónico está en `deploy/Caddyfile.boda`. Debe integrarse en el Caddyfile general sin alterar otros hosts. El upstream es `boda-wedding:8787`; no se publica ningún puerto del contenedor.

## Backups

`boda-wedding-backup.timer` corre diariamente y usa `sqlite3.backup`. Antes de cada deploy también se ejecuta un backup. Retención configurada: 45 días.

## Checks

```bash
docker ps --filter name=boda-wedding
docker exec caddy wget -qO- http://boda-wedding:8787/healthz
systemctl is-active boda-wedding-backup.timer
```

La workflow de GitHub **sólo valida** sintaxis/tests. No despliega ni depende de un runner del VPS.
