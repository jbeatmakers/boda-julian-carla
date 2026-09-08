# Invitación — Julián & Carla

Landing estática de casamiento + panel de administración.

- **Sitio:** https://boda-julian-carla.bpm.red
- **Repo:** https://github.com/jbeatmakers/boda-julian-carla
- **Pages:** rama `main` + CNAME `boda-julian-carla.bpm.red`

Si llegás como programador nuevo, leé [`docs/HANDOVER.md`](docs/HANDOVER.md).

## Qué hay

| Archivo | Rol |
|---|---|
| `index.html` | Invitación pública (gate `18dic`) |
| `admin.html` | Panel: invitados, súper, cantidades, mesas, contrataciones, pista |
| `pista.json` | Lista pública de temas + ID de playlist YouTube |
| `js/public-pista.js` | Pinta la pista en la invitación, sin mostrar quién pidió el tema |
| `CNAME` | Dominio custom |
| `robots.txt` | Bloquea indexación |

Zero-build. HTML + Tailwind CDN + JS. Sin backend.

## Correr en local

```bash
python3 -m http.server 8080
```

- Invitación: http://localhost:8080/
- Admin: http://localhost:8080/admin.html

## Evento

- Público: Julián & Carla (sin apellidos en el hero)
- Fecha: 18 de diciembre de 2026
- 17:00 Iglesia San Pedro y San Pablo, San Pablo de Reyes
- 18:30 El Quincho del Predio de Reyes
- Dress code: Estética Edén
- Regalos: voluntario, **sin montos**

## Panel (admin.html)

Tabs:

1. **Invitados** — RSVP, CSV, alta/edición
2. **Súper y cantidades** — ofertas (lugar, precio, cantidad) + cálculo automático de fernet/bebidas/hielo/vasos según cubiertos + presupuesto por invitado
3. **Mesas** — cubiertos ÷ personas por mesa
4. **Contrataciones** — DJ, foto, catering, etc.
5. **Pista** — temas anónimos + playlist YouTube (se escucha sin Premium)

Datos en `localStorage` de **ese** navegador. Backup JSON desde el panel.

Para que la pista se vea en todos los celulares: en Pista → “Sumar canciones de invitados” → “Descargar pista.json” → reemplazar el archivo en la raíz y push.

## Copy que no hay que romper

- No “Edición Nº 01”
- No “botánico” en la tarjeta
- No “Colegio de Abogados” en la tarjeta (decir Quincho / Predio de Reyes)
- No montos de regalo
- Al declinar: tono positivo
- Menú especial oculto detrás de un toggle

## Credenciales

Están en constantes de `index.html` (gate invitados) y `admin.html` (`AUTH_USER` / `AUTH_PASS`). No son seguridad real: es HTML público.
