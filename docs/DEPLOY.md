# Deploy

GitHub Pages sirve la raíz de `main`.

1. Push a `main`.
2. Esperar 1–2 minutos.
3. Verificar https://boda-julian-carla.bpm.red y `/admin.html`.

## Dominio

Archivo `CNAME` = `boda-julian-carla.bpm.red`.

Si cambia el dominio, actualizar `CNAME` y los meta `og:url` en `index.html`.

## Pista pública para todos los dispositivos

1. En admin, tab Pista: “Sumar canciones de invitados”.
2. Pegar ID de playlist YouTube (`list=`).
3. “Descargar pista.json”.
4. Reemplazar `pista.json` en la raíz y push.

Sin ese push, la lista anónima queda solo en el navegador donde se confirmó o se administró.

## Backup

En el panel: “Backup JSON” / “Importar JSON”. No se versiona (está en `.gitignore`).
