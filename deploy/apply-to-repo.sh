#!/usr/bin/env bash
set -euo pipefail
DEST=${1:?ruta del checkout del repo requerida}
SRC=$(cd "$(dirname "$0")/.." && pwd)
[[ -d "$DEST/.git" ]] || { echo "No parece un checkout Git: $DEST" >&2; exit 2; }
mkdir -p "$DEST/assets" "$DEST/server" "$DEST/deploy" "$DEST/tests" "$DEST/docs" "$DEST/.github/workflows"
cp "$SRC/index.html" "$SRC/admin.html" "$SRC/CNAME" "$SRC/robots.txt" "$SRC/README.md" "$DEST/"
cp "$SRC/assets/"* "$DEST/assets/"
cp "$SRC/server/"*.py "$DEST/server/"
cp "$SRC/deploy/"* "$DEST/deploy/"
cp "$SRC/tests/"*.py "$DEST/tests/"
cp "$SRC/docs/"*.md "$DEST/docs/"
cp "$SRC/.github/workflows/deploy-vps.yml" "$DEST/.github/workflows/deploy-vps.yml"
rm -f "$DEST/site-content.json" "$DEST/pista.json" "$DEST/js/public-pista.js"
rmdir "$DEST/js" 2>/dev/null || true
printf 'Aplicado. Revisar con: git status --short && python3 -m unittest -v tests.test_server tests.test_static\n'
