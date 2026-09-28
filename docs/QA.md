# QA de la release

## Contratos verificados automáticamente

- JavaScript público y admin pasan `node --check`.
- Backend y backup pasan `py_compile`.
- HTML parseable.
- `BODA` presente como código de invitados.
- La invitación no contiene `Colegio de Abogados` ni `Centro de Abogados` como copy visible.
- Coordenadas de ceremonia y celebración incluidas.
- No queda la contraseña administrativa histórica embebida en HTML/JS.
- RSVP persistente e idempotente.
- Login, sesión y CSRF.
- CRUD de invitados, gastos, compras, tareas y proveedores.
- Invitado con precio especial y sin cargo.
- Configuración de precio global desde admin.
- Orígenes web no autorizados bloqueados para RSVP.

## Regresión de ciclo de vida de la tarjeta

`tests/browser_lifecycle.py` ejecuta un backend y SQLite descartables; intercepta las solicitudes de los dominios de prueba y nunca envía RSVP a producción. La matriz de CI lo ejecuta en Chromium, Firefox y WebKit además de `browser_access.py`.

Cubre conservación del foco al actualizar configuración, visibilidad de Instagram definida por el administrador, recibos tardíos sin borrar borradores nuevos, vaciado del formulario confirmado desde la cola, reutilización del identificador persistido, recuperación del borrador durante una actualización de release, login/conciliación/altas/editor/vista previa/logout administrativos y navegación a 320/390/768/1280 píxeles con respuesta de no asistencia.

Las comprobaciones de producción siguen siendo de sólo lectura. Un resultado exitoso documenta los escenarios probados, no promete ausencia absoluta de errores en dispositivos o redes ajenos.

El control de orden de secciones también comprueba que el orden guardado en el administrador se conserve tanto al abrir la tarjeta como después de reiniciar el backend. `test_layout_order.py` cubre esa persistencia sin usar datos reales.

La administración se prueba con HTTPS nativo sobre loopback y un certificado efímero de un día. Se mantiene la cookie real `HttpOnly; Secure; SameSite=Strict`; no se inyectan sesiones ni se relajan las cookies del producto. El certificado autofirmado sólo se acepta en ese contexto de prueba local. El verificador contra producción continúa validando TLS normalmente.
