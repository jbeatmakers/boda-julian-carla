# Configuración actual

La invitación y el wedding planner se administran desde el panel; no se edita un JSON público a mano.

## Accesos

- Invitados: código público `BODA`.
- Administración: existe un código especial validado exclusivamente por el backend.
- Ninguna contraseña ni código administrativo debe escribirse en HTML, JS, tests, documentación o Git.
- Las credenciales privadas viven en el VPS y las contraseñas se almacenan como PBKDF2.

## Sitio & tarjeta

Desde el admin → **Sitio & tarjeta** se modifican:
- textos y títulos;
- valor y texto de tarjeta;
- datos de transferencia;
- ceremonia y celebración;
- coordenadas de mapas;
- dress code;
- fecha límite visible y WhatsApp de respaldo.

Los datos bancarios no tienen placeholders públicos: se cargan únicamente cuando correspondan desde el panel.

## Invitados y planificación

El panel administra cupos, confirmados, precios especiales/sin cargo, pagos, crédito por aportes, mesas, dietas, canciones y notas.

Sin override manual, el planificador estima sobre confirmados + cupos de invitados/pendientes y aplica el margen configurado. Los registros todavía marcados como “posible” no inflan compras.

Compras y aportes usan equivalencias por envase. Sólo los aportes marcados **Recibido** cuentan como stock.

## Backend

Variables privadas: `/etc/boda-julian-carla.env`.
Datos: `/var/lib/boda-julian-carla/wedding.sqlite3`.
Admin/API: `https://boda-api.13-140-183-198.sslip.io/`.

Si cambia una variable de entorno hay que **recrear** el contenedor:

```bash
sudo /usr/local/sbin/recreate-boda-wedding
```

Un simple `docker restart` no recarga el env-file.

## Instagram

Perfil objetivo: `@juli.y.carli`. El enlace al perfil funciona aun sin OAuth. El feed sólo se activa cuando Meta está autorizado y existen publicaciones. App Secret y tokens quedan exclusivamente en el VPS.
