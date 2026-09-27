# Operación y publicación de la boda

## Producción y fuente de verdad

El único enlace compartido con invitados es **https://bodajulianycarla.bpm.red/**, con la **y**. GitHub Pages sirve la tarjeta. La API pública usa `https://boda-api.bpm.red`; la dirección `https://boda-api.13-140-183-198.sslip.io` se conserva para administración y sesiones existentes. Ambas llegan al mismo contenedor `boda-wedding`, sin duplicar datos.

La base de datos está en `/var/lib/boda-julian-carla/wedding.sqlite3`. Código y administrador viven en `/opt/boda-julian-carla`. El entorno privado es `/etc/boda-julian-carla.env`; nunca se publica ni se copia al artefacto de Pages.

## Cadena obligatoria de publicación

`.github/workflows/deploy-vps.yml` es **Validate and publish wedding release**:

1. Comprueba sintaxis, contratos, pruebas unitarias y pruebas de persistencia/seguridad.
2. Ejecuta navegadores Chromium, Firefox y WebKit contra una API local y una SQLite temporal. Incluye BODA, almacenamiento denegado, API caída, recuperación, confirmación persistida y respuestas inválidas.
3. Verifica en producción que el hash del backend en ejecución coincide con el código probado. Un cambio pendiente de backend bloquea la publicación pública.
4. Construye `_site` desde una lista cerrada de archivos públicos. El artefacto no incluye administrador, servidor, tests ni secretos. `release.json` registra el commit y el SHA-256 de cada archivo.
5. Publica **ese mismo artefacto**, únicamente después de todos los controles anteriores.
6. Reabre el dominio con la y, compara archivos servidos y commit, verifica API/SQLite/CORS y ejecuta pruebas de navegador contra producción sin modificar invitados.

Pages debe tener `build_type: workflow`. No volver al despliegue automático de la raíz de `main`, que publicaba aunque la validación independiente fallara. El dominio personalizado y HTTPS obligatorio se conservan en la configuración de Pages.

## Cambios del backend

El workflow no recibe credenciales administrativas ni reemplaza datos. Para un cambio de servidor, usar la conexión SSH autorizada y desplegar la revisión probada **antes** de que el pipeline publique el cliente correspondiente:

```bash
sudo /usr/local/sbin/deploy-boda-julian-carla /ruta/al/checkout
```

El helper realiza copia de seguridad de código y SQLite. Al actualizar variables o la IP del proxy, instalar la versión revisada de `deploy/recreate-container.sh` y ejecutar `/usr/local/sbin/recreate-boda-wedding`. Reiniciar solamente el contenedor no recarga variables.

Caddy sobrescribe `X-Wedding-Client-IP` con la IP real de conexión. El backend sólo acepta ese encabezado desde la IP exacta de Caddy en la red privada `web`, declarada en `WEDDING_TRUSTED_PROXIES`. Sin una fuente confiable no se aceptan encabezados suministrados por clientes. Esto evita compartir entre todos los invitados el límite de envíos del proxy.

El bloque de la boda está delimitado por `BEGIN BODA JULIAN CARLA` y `END BODA JULIAN CARLA` en `/opt/apps/_proxy/Caddyfile`. Copiarlo con respaldo, validar y recargar sin alterar otros servicios. El registro DNS `A boda-api` apunta al VPS y Caddy administra su certificado HTTPS.

## Acceso y errores de conexión

BODA es una puerta social, no una credencial de administración. Una clave BODA válida abre la tarjeta sin esperar la API. Si aún no llegaron datos actuales, no se inventan precios ni datos bancarios: se ocultan y se muestra el estado de actualización con reintento. Una falla de configuración no vuelve a cerrar la tarjeta.

El envío de RSVP sólo se anuncia como confirmado después de recibir `ok: true` y un identificador del servidor. La misma respuesta conserva su `request_id` al reintentar; el servidor serializa duplicados. Cuando el navegador impide persistir una respuesta, la interfaz lo dice y conserva el formulario y una cola en memoria mientras permanezca abierta la página.

## Caché y versiones

Todo cambio en archivos públicos debe actualizar `wedding-release` y las versiones de assets de `index.html`; `actualizar.html` debe usar la misma release. El actualizador conserva borradores durante cambios de release. `js/public-pista.js` recupera HTML retirado que todavía solicite ese archivo. No puede ejecutarse código nuevo dentro de una pestaña antigua que no haga ninguna solicitud de red.

La redirección histórica del dominio sin la y no es la causa de este incidente, ni sustituye ninguna prueba del dominio oficial. No crear otra aplicación allí.

## Diagnóstico y backups

`Wedding production diagnostic` es manual y no necesita secretos SSH: verifica los bytes publicados, el backend en ejecución, lectura real de SQLite, CORS y apertura BODA con navegador. Las pruebas no envían RSVP a producción. El endpoint `/healthz` devuelve 503 si SQLite no está disponible y expone sólo salud y huella de código, nunca invitados ni credenciales.

El timer `boda-wedding-backup.timer` utiliza la API de backup de SQLite; la retención configurada es de 45 días. Una prueba local o un workflow exitoso no sustituyen la comparación posterior con producción.
