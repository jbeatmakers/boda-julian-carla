#!/usr/bin/env bash
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo "Ejecutar como root." >&2; exit 2; }
ENV=/etc/boda-julian-carla.env
[[ -f "$ENV" ]] || { echo "Falta $ENV" >&2; exit 3; }
docker network inspect web >/dev/null
docker rm -f boda-wedding >/dev/null 2>&1 || true
docker run -d --name boda-wedding --restart unless-stopped --network web \
  --env-file "$ENV" \
  -v /var/lib/boda-julian-carla:/var/lib/boda-julian-carla \
  -v /opt/boda-julian-carla/server:/opt/boda-julian-carla/server:ro \
  -v /opt/boda-julian-carla/admin:/opt/boda-julian-carla/admin:ro \
  -w /opt/boda-julian-carla/server \
  python:3.12-alpine python app.py >/dev/null
for _ in $(seq 1 20); do
  if docker exec caddy wget -qO- http://boda-wedding:8787/healthz | grep -q '"ok":true'; then
    echo "boda-wedding OK"; exit 0
  fi
  sleep 1
done
docker logs --tail 80 boda-wedding >&2
exit 1
