#!/usr/bin/env bash
# Primera instalación/recuperación de la boda en el VPS Docker+Caddy.
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo "Ejecutar como root." >&2; exit 2; }
SRC=${1:?ruta de release requerida}
for f in admin.html assets/admin.css assets/admin.js server/app.py server/backup.py; do
  [[ -f "$SRC/$f" ]] || { echo "falta $f" >&2; exit 3; }
done
id boda-wedding >/dev/null 2>&1 || useradd --system --home /nonexistent --shell /usr/sbin/nologin boda-wedding
install -d -o root -g root -m 0755 /opt/boda-julian-carla/{admin,admin/assets,server}
install -d -o boda-wedding -g boda-wedding -m 0750 /var/lib/boda-julian-carla /var/backups/boda-julian-carla
install -m 0644 "$SRC/admin.html" /opt/boda-julian-carla/admin/admin.html
install -m 0644 "$SRC/assets/admin.css" "$SRC/assets/admin.js" /opt/boda-julian-carla/admin/assets/
install -m 0755 "$SRC/server/app.py" "$SRC/server/backup.py" /opt/boda-julian-carla/server/
install -m 0755 "$SRC/deploy/recreate-container.sh" /usr/local/sbin/recreate-boda-wedding
install -m 0755 "$SRC/deploy/deploy-boda-julian-carla" /usr/local/sbin/deploy-boda-julian-carla
install -m 0644 "$SRC/deploy/boda-wedding-backup.service" "$SRC/deploy/boda-wedding-backup.timer" /etc/systemd/system/
if [[ ! -f /etc/boda-julian-carla.env ]]; then
  install -m 0600 "$SRC/deploy/env.example" /etc/boda-julian-carla.env
  echo "Editá /etc/boda-julian-carla.env y ejecutá deploy/configure-admin.sh." >&2
  exit 4
fi
systemctl daemon-reload
systemctl enable --now boda-wedding-backup.timer >/dev/null
/usr/local/sbin/recreate-boda-wedding
echo "Runtime OK. Verificá también el bloque deploy/Caddyfile.boda en el Caddy general."
