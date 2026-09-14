# Deploy al VPS

La release está preparada para sacar el runtime de GitHub Pages y dejar GitHub solo como repositorio/versionado.

## 1. DNS

Apuntar al VPS:

- `boda-api.bpm.red`
- `boda-julian-carla.bpm.red` cuando se haga el corte definitivo desde GitHub Pages al VPS.

Durante la transición el frontend ya apunta a `https://boda-api.bpm.red`, por lo que el backend compartido puede empezar a funcionar antes del corte final del dominio público.

## 2. Primera instalación

Desde una copia de esta release en el VPS:

```bash
sudo ./deploy/deploy-release.sh /ruta/a/la/release
sudo ./deploy/configure-admin.sh
```

`configure-admin.sh` solicita la contraseña sin imprimirla y guarda únicamente el hash PBKDF2 en `/etc/boda-julian-carla.env`.

## 3. Nginx y TLS

El archivo `deploy/nginx-boda.conf` contiene los dos virtual hosts y cabeceras de seguridad. Requiere certificados Let's Encrypt para ambos dominios. No se incluyen claves ni certificados en el repo.

Luego de instalar/verificar certificados, habilitar el site, ejecutar `nginx -t` y recargar Nginx.

## 4. Comprobar

```bash
curl -fsS http://127.0.0.1:8787/healthz
systemctl is-active boda-wedding.service
systemctl is-active boda-wedding-backup.timer
```

En navegador:

- invitación: `https://boda-julian-carla.bpm.red/`
- admin: `https://boda-api.bpm.red/`

## 5. Runner self-hosted opcional

La workflow `.github/workflows/deploy-vps.yml` solo acepta `push` a `main` del repo exacto o ejecución manual. No usa GitHub-hosted runners.

El runner debe tener permiso `sudo` únicamente para `/usr/local/sbin/deploy-boda-julian-carla`; el helper root copia archivos conocidos y reinicia únicamente el servicio de la boda.

Si el runner se cae o GitHub no responde, **el sitio, RSVP, panel y base siguen funcionando**. Solo queda pendiente el próximo deploy.
