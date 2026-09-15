# Corrección de checkout y envío de leads

## Causa verificada

La orden `ORD-MUJCQB69FJRG` estaba PENDING en SQLite, mientras Stripe tenía su Checkout en `complete / paid`: cuatro leads, USD 60.00, modo test. Stripe no tenía endpoints de webhook registrados y no se encontró un proceso `stripe listen`. El GET de estado solo leía SQLite; nunca verificaba el pago ni iniciaba asignación/correo.

## Cambio

- GET de la orden sigue siendo de solo lectura.
- Nuevo POST `/api/v1/purchases/{public_id}/refresh`: Stripe recupera la sesión guardada por el servidor. El ID, `client_reference_id` y metadata deben pertenecer a esa orden. Nunca se confía en un estado de pago o sesión enviados por el navegador.
- Reutiliza `FulfillmentService` y `EmailService`, con validación de importe/moneda, inventario y protección contra asignación y correo duplicados. Los pagos no confirmados no reciben leads.
- Lock por orden entre procesos y cooldown persistido de 15 segundos reducen las llamadas repetidas al proveedor.
- Tarea de recuperación cada 60 segundos con el scheduler existente. Revisa hasta 10 órdenes por ejecución, priorizando las menos recientemente revisadas y limitando el barrido a órdenes de los últimos siete días. Órdenes más antiguas pueden verificarse explícitamente.
- Los fallos del correo conservan la asignación y generan un error específico en español. Un intento posterior reutiliza la clave de idempotencia de entrega. Se registra el ID aceptado por Resend en auditoría, sin exponerlo en la respuesta pública.
- El frontend verifica cuando falta pago/correo, detiene las consultas al completar y aumenta los intervalos de 2 a 10 segundos. Tras 12 intentos muestra un aviso para actualizar después, sin repetir el pago. Conserva AbortController y captura cancelaciones intencionales.
- Los webhooks firmados siguen siendo la vía principal. El respaldo no elimina la necesidad de configurarlos en un despliegue público. Referencia: https://docs.stripe.com/checkout/fulfillment.

## Orden reportada

El intento de ejecutar una recuperación manual fue rechazado por la revisión automática de permisos porque asignaría y enviaría datos de leads a la dirección de la compra. Ese comando no se ejecutó ni se reintentó.

El backend local existente estaba ejecutándose con `uvicorn --reload`. Su recarga automática activó la nueva tarea programada, que completó la orden a las **00:35:48 del 14 de septiembre, hora de Puerto Rico**. La comprobación posterior de solo lectura confirmó:

- FULFILLED, cuatro asignaciones y `email_sent_at` registrado.
- Destinatario de la compra: `diegotechtools@gmail.com`.
- Resend aceptó el envío; ID registrado: `d962250f-2d6c-49fc-897f-5483b4b76c79`.
- La consulta de entrega a Resend devolvió HTTP 401. La aceptación del envío está verificada; la llegada a la bandeja de entrada no pudo comprobarse por API.
- Navegador: una sola consulta al abrir la orden completada; ninguna adicional durante 5.5 segundos. Navegar a leads y volver añade solo la consulta esperada, sin AbortError ni errores JavaScript. En esa verificación se bloquearon todos los POST de compras para garantizar solo lectura.

## Operación

Mantener el backend activo y `SCHEDULER_ENABLED=true` para recuperación sin navegador. Con el scheduler desactivado, el POST de regreso/actualización y los webhooks aún pueden procesar la orden. Resend debe permitir el remitente/destinatario configurado; el remitente de prueba actual no se cambió. No se rotaron claves, no se cobraron pagos nuevos y no se crearon órdenes nuevas para verificar esta corrección.

## Validación final

- Ruff: aprobado; backend: **123 pruebas aprobadas**. Se conservan dos advertencias de deprecación existentes de Starlette/AnyIO.
- Frontend: lint, TypeScript, formato y build de producción aprobados.
- Navegador: **28 casos aprobados** en total. La ejecución completa pasó 27; el nuevo caso de error de correo inicialmente encontraba también el anunciador de rutas de Next.js. Se limitó su selector de alerta al contenido principal y pasó al repetirlo. La cobertura funcional no se redujo.
- Cobertura nueva: recuperación sin webhook, ejecución sin regreso del navegador, pagos no confirmados, datos de pago falsificados, sesión ajena, error real de Stripe, cooldown, error/reintento de correo, webhook concurrente, parada de polling y origen del proxy.
- Las pruebas de escritura usan fixtures aislados. La comprobación de la orden reportada después de su recuperación automática fue de solo lectura.

## Corrección posterior: rechazos permanentes de correo

Se detectó que la recuperación repetía cada minuto órdenes históricas con destinatarios inválidos o no permitidos por el remitente de prueba de Resend. Los errores 422 de destinatario y 403 de validación no se resuelven repitiendo la misma petición.

- El adaptador clasifica los rechazos HTTP 400/401/403/404/405/413/422 y el 409 `invalid_idempotent_request` como bloqueos que requieren corrección. Los timeouts, 408, 409 por concurrencia, 429 y 5xx permanecen reintentables.
- El primer rechazo permanente registra `email.blocked` con código y categoría del proveedor, sin copiar destinatarios ni el cuerpo completo del error al log. No marca el correo como enviado ni altera la asignación de leads.
- Scheduler, webhooks repetidos y actualización pública respetan ese bloqueo, incluso tras reiniciar. Los barridos excluyen las órdenes bloqueadas antes de aplicar su límite, evitando que desplacen a compras válidas.
- La interfaz muestra `email_delivery_blocked` en español con indicación de revisión administrativa. El error permanece visible; no se oculta ni se convierte en un envío exitoso.
- Tras corregir destinatario/remitente/configuración, un administrador puede usar el endpoint existente `POST /api/v1/admin/purchases/{public_id}/resend-email` con autorización e `Idempotency-Key`. Solo un envío confirmado levanta el bloqueo. Un fallo transitorio de ese intento administrativo no habilita reintentos automáticos ocultos.
- No se cambiaron destinatarios, claves ni DNS, ni se iniciaron reenvíos manuales. Las verificaciones funcionales usan correos simulados.

Los registros locales de `ORD-A7AAEMC276GC` y `ORD-8X2A2XM2GTH7` muestran bloqueos persistidos por 422 y 403 respectivamente. Para destinatarios externos al correo del propietario, Resend exige verificar un dominio y utilizarlo en `from`: https://resend.com/docs/api-reference/errors. Los correos de ejemplo tampoco son destinatarios reales; no se redirigen automáticamente a otra persona.

Validación de esta corrección: 137 pruebas de backend y nueve pruebas de navegador aprobadas, además de Ruff, lint y build con TypeScript. La consulta de solo lectura a las 04:54:49 UTC confirmó que ambos bloqueos permanecían en un único registro por orden desde las 04:52:15 UTC, sin nuevos intentos de entrega durante más de dos ciclos del scheduler.
