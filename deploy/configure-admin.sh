#!/usr/bin/env bash
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo "Ejecutar como root." >&2; exit 2; }
APP=/opt/boda-julian-carla/server/app.py
[[ -f "$APP" ]] || { echo "Primero instalá la release." >&2; exit 3; }
read -r -p "Usuario admin [admin]: " USERNAME
USERNAME="${USERNAME:-admin}"
HASH=$(python3 "$APP" --hash-password)
ENV=/etc/boda-julian-carla.env
python3 - "$ENV" "$USERNAME" "$HASH" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); user=sys.argv[2]; h=sys.argv[3]
lines=p.read_text().splitlines() if p.exists() else []
def put(key,val):
    global lines
    pref=key+'='
    for i,x in enumerate(lines):
        if x.startswith(pref): lines[i]=pref+val; return
    lines.append(pref+val)
put('WEDDING_ADMIN_USER',user); put('WEDDING_ADMIN_PASSWORD_HASH',h)
p.write_text('\n'.join(lines)+'\n')
PY
chmod 600 "$ENV"
systemctl restart boda-wedding.service
systemctl --no-pager --full status boda-wedding.service | sed -n '1,12p'
