# QA de la release

## Contratos verificados automáticamente

- JavaScript público y admin pasan `node --check`.
- Backend y backup pasan `py_compile`.
- HTML parseable.
- `18DIC` presente como código de invitados.
- La invitación no contiene `Colegio de Abogados` ni `Centro de Abogados` como copy visible.
- Coordenadas de ceremonia y celebración incluidas.
- No queda la contraseña administrativa histórica embebida en HTML/JS.
- RSVP persistente e idempotente.
- Login, sesión y CSRF.
- CRUD de invitados, gastos, compras, tareas y proveedores.
- Invitado con precio especial y sin cargo.
- Configuración de precio global desde admin.
- Orígenes web no autorizados bloqueados para RSVP.
