# Auditoría de cierre

Fecha de revisión: 2026-09-08. Repo `jbeatmakers/boda-julian-carla` @ `main`.

## Pedidos de producto

| Pedido | Estado | Notas |
|---|---|---|
| Tarjeta digital RSVP + pago | Hecho | WhatsApp + alias/CBU/MP voluntario |
| Estética Edén (no decir botánico en copy) | Hecho | Sección dress code |
| Sin Edición Nº 01 | Hecho | |
| Sin apellidos en el hero | Hecho | Apellidos solo en titulares bancarios |
| Fecha 18 dic 2026 | Hecho | Countdown 17:00 ART |
| Ceremonia 17:00 iglesia cerca Reyes | Hecho | San Pedro y San Pablo + Maps |
| Fiesta 18:30 quincho, sin “Colegio de Abogados” | Hecho | Quincho del Predio de Reyes + Maps |
| Menú especial poco accesible | Hecho | Toggle “+ restricción alimentaria” |
| Sin montos de regalo | Hecho | Colaboración libre |
| Declinar con tono positivo | Hecho | “Brindaremos y festejaremos teniéndote muy presente” |
| Ofertas del súper (lugar, precio, cant.) | Hecho | Admin → Súper y cantidades |
| Contar cantidades (fernet, litros/persona) | Hecho | Provisiones automáticas vs comprado |
| Mesas según invitados | Hecho | Admin → Mesas |
| Contrataciones (DJ, foto, etc.) | Hecho | Admin → Contrataciones |
| Pista pública anónima | Hecho | `index` sección Temas de la fiesta |
| Reproductor gratis | Hecho | YouTube playlist embed |
| Repo prolijo para otro programador | Hecho | README + docs/HANDOVER + CONFIG + DEPLOY |

## Archivos en raíz

- `index.html` invitación
- `admin.html` panel
- `pista.json` lista pública
- `js/public-pista.js`
- `CNAME` → boda-julian-carla.bpm.red
- `robots.txt` noindex
- `README.md` `.gitignore`
- `docs/HANDOVER.md` `docs/DEPLOY.md` `docs/CONFIG.md` `docs/CHECKLIST.md`

## Pendiente operativo (no es código)

1. WhatsApp, alias, CBU, MP reales (Admin → Ajustes).
2. Crear playlist YouTube pública y pegar el ID.
3. Tras las primeras RSVP: exportar `pista.json` y pushearlo.
4. Backup JSON periódico del panel (vive en un solo navegador).
5. Webhook opcional si quieren que las RSVP no dependan de localStorage.
