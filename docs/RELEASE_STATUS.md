# Estado de la release

## Terminado en código

- Invitación pública v2.
- Acceso `BODA`.
- Mapas exactos y navegación.
- Confetti liviano al entrar y al abrir direcciones.
- RSVP persistente + reintento offline.
- Copy de asistencia/no asistencia y regalos.
- Precio de tarjeta editable.
- Admin seguro y compartido.
- Invitados con precio general/especial/sin cargo, pagos, regalos y mesas.
- Gastos, compras, tareas, proveedores y checklist base.
- Importación del backup legado.
- Backups automáticos del VPS.
- Workflow self-hosted opcional y helper de privilegio acotado.
- Tests backend/security/static.

## Cambio de infraestructura necesario para quedar en producción

Hace falta aplicar estos archivos al repo/VPS y configurar DNS/TLS del nuevo backend. Eso no se codifica como secreto dentro de la release: la contraseña admin, DNS y certificados pertenecen al entorno del VPS.
