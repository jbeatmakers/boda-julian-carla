#!/usr/bin/env bash
set -euo pipefail
SRC="${1:-$(pwd)}"
[[ $EUID -eq 0 ]] || { echo "Ejecutar como root." >&2; exit 2; }
id boda-wedding >/dev/null 2>&1 || useradd --system --home /nonexistent --shell /usr/sbin/nologin boda-wedding
install -d -o root -g root -m 0755 /opt/boda-julian-carla/{public,public/assets,admin,admin/assets,server}
install -d -o boda-wedding -g boda-wedding -m 0700 /var/lib/boda-julian-carla /var/backups/boda-julian-carla
install -m 0644 "$SRC/index.html" /opt/boda-julian-carla/public/index.html
install -m 0644 "$SRC/assets/styles.css" "$SRC/assets/app.js" /opt/boda-julian-carla/public/assets/
install -m 0644 "$SRC/admin.html" /opt/boda-julian-carla/admin/admin.html
install -m 0644 "$SRC/assets/admin.css" "$SRC/assets/admin.js" /opt/boda-julian-carla/admin/assets/
install -m 0755 "$SRC/server/app.py" "$SRC/server/backup.py" /opt/boda-julian-carla/server/
install -m 0755 "$SRC/deploy/deploy-boda-julian-carla" /usr/local/sbin/deploy-boda-julian-carla
install -m 0644 "$SRC/deploy/boda-wedding.service" "$SRC/deploy/boda-wedding-backup.service" "$SRC/deploy/boda-wedding-backup.timer" /etc/systemd/system/
if [[ ! -f /etc/boda-julian-carla.env ]]; then
  install -m 0600 "$SRC/deploy/env.example" /etc/boda-julian-carla.env
  echo "ATENCIÓN: configurá WEDDING_ADMIN_PASSWORD_HASH en /etc/boda-julian-carla.env antes de iniciar el servicio." >&2
fi
systemctl daemon-reload
systemctl enable boda-wedding.service boda-wedding-backup.timer >/dev/null
if ! grep -q '^WEDDING_ADMIN_PASSWORD_HASH=pbkdf2_sha256\$' /etc/boda-julian-carla.env; then
  echo "Release instalada; servicio NO reiniciado porque falta una contraseña admin segura." >&2
  exit 3
fi
systemctl restart boda-wedding.service
systemctl start boda-wedding-backup.timer
systemctl --no-pager --full status boda-wedding.service | sed -n '1,12p'
