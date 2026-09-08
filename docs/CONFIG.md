# Configuración — qué editar y dónde

Nada se compila. Cambiar, commit, push a `main`.

## Invitación (`index.html`)

| Dato | Dónde |
|---|---|
| Fecha / countdown | `targetDate = new Date("2026-12-18T17:00:00-03:00")` y textos 18 · XII · 2026 |
| Horarios | 17:00 ceremonia / 18:30 fiesta |
| Iglesia | San Pedro y San Pablo, Carlos Figueroa, San Pablo de Reyes |
| Fiesta | El Quincho del Predio de Reyes (no escribir Colegio de Abogados) |
| Gate invitados | `checkPassword()` compara con `18dic` |
| Hero | Solo Julián & Carla (sin apellidos) |
| Titulares transferencia | Julián Morales & Carla Quiroga |
| Alias / CBU / MP | Defaults en `getConfig()`; el admin los pisa vía `localStorage` `boda_julian_carla_config` |

## Admin (`admin.html`)

| Dato | Dónde |
|---|---|
| Usuario / clave panel | `AUTH_USER` / `AUTH_PASS` (arriba del `<script>`) |
| WhatsApp receptor | Ajustes → número internacional sin + |
| Webhook RSVP | Ajustes → URL (opcional, POST JSON) |
| Alias / CBU / MP | Ajustes |
| Playlist YouTube | Tab Pista → ID `list=` |

Keys `localStorage` (mismo origen):

- `boda_julian_carla_guests`
- `boda_julian_carla_config`
- `boda_julian_carla_shopping`
- `boda_julian_carla_offers`
- `boda_julian_carla_vendors`
- `boda_julian_carla_tables`
- `boda_julian_carla_pista`
- `boda_julian_carla_rates`

## Pista pública (`pista.json` + `js/public-pista.js`)

```json
{
  "youtubePlaylistId": "PLxxxxxxxx",
  "songs": [{ "title": "Tema — Artista" }]
}
```

Flujo: RSVP guarda el tema anónimo → Admin Pista “Sumar canciones de invitados” → Descargar `pista.json` → reemplazar en la raíz → push. Sin ese push, el resto de invitados no ve la lista.

YouTube se escucha sin Premium. No usar Spotify.

## Placeholders que siguen vacíos (los novios / el dev tienen que completar)

- Número WhatsApp real
- Alias y CBU reales
- Link Mercado Pago de monto libre
- ID de playlist YouTube
