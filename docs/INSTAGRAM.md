# Instagram de la boda

Cuenta objetivo: `@juli.y.carli`.

## Comportamiento público

La invitación muestra siempre el enlace al perfil. Si todavía no hay publicaciones o Meta no está conectado, muestra un estado vacío amable. Cuando el backend dispone de publicaciones autorizadas, el mismo bloque se transforma en una galería de hasta 6 elementos.

Nunca se inventan fotos ni se hace scraping privado.

## Arquitectura

- El navegador nunca recibe App Secret ni access token.
- `/api/public/instagram` devuelve sólo username, URL pública y publicaciones sanitizadas.
- OAuth y tokens se guardan fuera de GitHub en el VPS.
- El archivo privado de autorización es `WEDDING_INSTAGRAM_AUTH_PATH`.
- El cache/feed privado es `WEDDING_INSTAGRAM_FEED_PATH`.
- Las imágenes siempre enlazan a la publicación original.

## Meta

App de Meta: `Boda Julian y Carla` (App ID público configurado en backend).
La vía implementada es Instagram API con Facebook Login. La autorización busca específicamente una Page administrada cuya `instagram_business_account.username` sea `juli.y.carli`.

Permisos solicitados por OAuth:
- `pages_show_list`
- `pages_read_engagement`
- `instagram_basic`

No se solicitan permisos de publicación, mensajes o comentarios para el feed de la tarjeta. El App Secret debe existir sólo en `/etc/boda-julian-carla.env`; al cambiarlo hay que **recrear** `boda-wedding`, no sólo reiniciarlo.
