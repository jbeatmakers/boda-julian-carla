# Migración del panel anterior

El panel anterior guardaba invitados y organización en `localStorage`; por eso una computadora podía tener datos que otra no veía.

## Camino seguro

1. En el panel anterior, usar `Backup` y descargar el JSON.
2. En el panel nuevo, botón `Importar` y elegir ese JSON.
3. La importación suma datos; no borra la base actual.
4. Verificar invitados, precios especiales y estados.
5. Guardar un backup nuevo desde el panel.

El importador reconoce invitados, proveedores, checklist/tareas, pista de canciones y configuración principal del backup viejo. El archivo original conviene conservarlo como evidencia hasta terminar la revisión.
