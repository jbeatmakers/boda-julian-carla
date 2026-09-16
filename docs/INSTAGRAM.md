# Instagram de la boda

La tarjeta tiene una sección de Instagram preparada y oculta por defecto. Solo se muestra cuando el backend devuelve publicaciones autorizadas.

## Arquitectura

- El navegador nunca recibe tokens de Meta.
- El backend expone `/api/public/instagram` con hasta 6 publicaciones sanitizadas.
- Mientras no exista una conexión válida, responde `enabled: false` y la sección permanece oculta.
- El feed autorizado se conserva en un archivo privado del VPS (`WEDDING_INSTAGRAM_FEED_PATH`), fuera de GitHub.
- Las imágenes enlazan a la publicación original de Instagram.

## Conexión prevista

Para usar una cuenta Meta/Facebook distinta del login de Instagram, la vía prevista es Instagram API with Facebook Login. La cuenta de Instagram debe ser profesional (Business o Creator) y estar vinculada a una Facebook Page. El usuario de Meta que autoriza debe tener acceso a esa Page/activo de negocio.

Permisos mínimos previstos para leer el perfil y publicaciones propias:

- `pages_show_list`
- `pages_read_engagement`
- `instagram_basic`

No se solicitarán permisos de publicación, mensajes o comentarios si el sitio solo va a mostrar el feed.
