# Configuración — qué editar y dónde

Nada se compila. Cambiar, commit, push a `main`.

## Contenido del sitio (`site-content.json`)

Fuente de verdad unificada para la landing pública:

```json
{
  "couple": "Julián & Carla",
  "date": "2026-12-18",
  "dateDisplay": "18 de Diciembre de 2026",
  "dateDisplayShort": "18 · XII · 2026",
  "locationDisplay": "San Pablo de Reyes · Jujuy",
  "ceremony": {
    "time": "17:00",
    "title": "Santa Misa de Casamiento",
    "place": "Iglesia San Pedro y San Pablo",
    "address": "Calle Carlos Figueroa · San Pablo de Reyes · Jujuy",
    "gpsUrl": "https://maps.google.com/?q=..."
  },
  "celebration": {
    "time": "18:30",
    "title": "Recepción, cena & fiesta",
    "place": "El Quincho del Predio de Reyes",
    "address": "A 4 cuadras de la ceremonia · San Pablo de Reyes",
    "gpsUrl": "https://maps.google.com/?q=..."
  },
  "dressCode": {
    "title": "Estética Edén",
    "concept": "Inspirado en la naturaleza al atardecer...",
    "women": "Vestido formal en paleta natural...",
    "men": "Traje formal con corbata o moño...",
    "note": "No hace falta comprar de nuevo..."
  },
  "ticket": {
    "enabled": true,
    "price": 35000,
    "currency": "ARS",
    "title": "Tarjeta de Casamiento",
    "description": "..."
  },
  "bank": {
    "holder": "Julián Morales & Carla Quiroga",
    "alias": "JULIAN.Y.CARLA.BODA",
    "cbu": "0070012345678901234567",
    "mpUrl": "https://mpago.la/LINK_LIBRE"
  }
}
```

Para editarlo: entrar al Admin → Pestaña **Sitio & Tarjeta** → Modificar campos → "Descargar site-content.json" → reemplazar en la raíz y commitear.

## Invitación (`index.html`)

- Carga automáticamente `site-content.json` con fallback a `localStorage` y defaults en el cliente.
- Gate de acceso para invitados: contraseña `18dic`.
- Formulario RSVP registra nombre, WhatsApp, email, cupo, restricciones alimentarias, tema musical y dedicatoria.
- Genera mensaje preformateado y redirige al WhatsApp de los novios.

## Admin (`admin.html`)

- Credenciales por defecto: usuario `julianycarla` / contraseña `5pamplona`.
- Pestañas disponibles:
  - **Invitados**: Filtros por estado (`confirmado`, `pendiente`, `posible`, `no_asiste`, `diet`), edición, teléfono, mail y exportación CSV.
  - **Súper & Bebidas**: Stock actual con envases específicos, ofertas de compra y provisiones automáticas según cubiertos confirmados.
  - **Mesas**: Distribución automática configurable (por defecto 8 sillas por mesa).
  - **Equipo**: Registro de proveedores, costos y señas.
  - **Pista**: Gestión de temas solicitados por invitados, ID de playlist de YouTube y descarga de `pista.json`.
  - **Sitio & Tarjeta**: Control editorial de textos, GPS y precio unitario de tarjeta con cálculo en tiempo real de recaudación proyectada.
