# Handover — Boda Julián & Carla

Sitio: https://boda-julian-carla.bpm.red  
Repo: https://github.com/jbeatmakers/boda-julian-carla  
Pages: rama `main` + CNAME `boda-julian-carla.bpm.red`

## Qué es

Landing estática (GitHub Pages, zero-build) + panel `admin.html`.  
RSVP abre WhatsApp y guarda el registro en `localStorage`. No hay servidor propio.

## Evento

| Campo | Valor |
|---|---|
| Público | Julián & Carla (sin apellidos en el hero) |
| Titulares bancarios | Julián Morales & Carla Quiroga |
| Fecha | 18 de diciembre de 2026 |
| Ceremonia | 17:00 Iglesia San Pedro y San Pablo, Carlos Figueroa, San Pablo de Reyes |
| Fiesta | 18:30 El Quincho del Predio de Reyes (no decir “Colegio de Abogados” en la tarjeta) |
| Dress code | Estética Edén (no usar la palabra “botánico” en el copy) |
| Gate invitados | `18dic` (client-side) |
| Admin | `AUTH_USER` / `AUTH_PASS` en `admin.html` |

## Decisiones de producto (no revertir)

- Sin “Edición Nº 01”.
- Sin montos de regalo. Colaboración voluntaria.
- Menú especial oculto detrás de un toggle.
- Al declinar: tono positivo.
- Pista pública: títulos anónimos, nunca el nombre del invitado.
- Reproductor: YouTube (gratis, sin Premium). No Spotify.

## Persistencia

- `boda_julian_carla_guests`
- `boda_julian_carla_config`
- `boda_julian_carla_shopping`
- `boda_julian_carla_offers`
- `boda_julian_carla_vendors`
- `boda_julian_carla_tables`
- `boda_julian_carla_pista`
- `boda_julian_carla_rates`

La pista visible para **todos** los invitados se publica en `pista.json` (exportar desde el panel y commitear). `localStorage` solo se ve en esa computadora.

## Placeholders

WhatsApp receptor, alias, CBU, link MP, playlist de YouTube: Admin → Ajustes / tab Pista.

## Local

```bash
python3 -m http.server 8080
```
