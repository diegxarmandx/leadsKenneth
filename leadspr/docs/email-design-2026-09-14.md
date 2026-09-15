# Correo de entrega FSG

La entrega de leads ahora usa un asunto y etiquetas en español, el logo original de Financial Support Group Inc., un resumen de compra y fichas azul marino con enlaces de teléfono y correo. Los nombres aparecen como encabezados de cada ficha; la versión de texto simple conserva las etiquetas de nombre y apellido por separado. Los valores recibidos del lead se conservan, incluidas las notas y sus saltos de línea.

## Vista previa

Datos ficticios, generados con la misma función que usa el servicio de entrega:

- [HTML para abrir en el navegador](previews/email-fsg.html)
- [Escritorio](previews/email-fsg-desktop.png)
- [Móvil](previews/email-fsg-mobile.png)

El HTML de vista previa sustituye exclusivamente la referencia CID del logo por sus mismos bytes en una URL de datos para poder abrirlo fuera de un cliente de correo.

## Implementación

- `backend/app/integrations/email/template.py`: datos, escape HTML, enlaces, asunto y versión de texto.
- `backend/app/integrations/email/assets/delivery.html`: estructura con tablas, estilos inline, ancho fluido y soporte de ancho para Outlook clásico.
- `backend/app/integrations/email/assets/logo-fsg.jpg`: copia exacta del logo proporcionado, incluida en el backend para evitar depender del despliegue del frontend.

El logo se adjunta mediante `content_id` y contenido Base64, según la [documentación de imágenes inline de Resend](https://resend.com/docs/dashboard/emails/embed-inline-images). La dirección de envío configurada se conserva. El antiguo nombre de empresa `LeadsPR` se presenta como `FSG Seguros`; también se actualiza el nombre visible del remitente cuando todavía dice `LeadsPR`. Se respetan los nombres personalizados de otras empresas.

El cambio no modifica los destinatarios, asignaciones, claves de idempotencia ni la política de reintentos. No reenvía correos históricos. No se enviaron correos reales para validar el diseño.

## Validación

- Ruff: sin errores.
- Pytest: 142 pruebas aprobadas; dos avisos existentes de dependencias Starlette/AnyIO.
- Chrome: ocho comprobaciones, combinando contenido habitual y largo con anchos de 320, 390, 768 y 1000 px; sin desbordamiento horizontal ni errores JavaScript, con logo visible.
- Enlaces de llamada y correo accesibles por teclado en las ocho comprobaciones.
- Axe WCAG A/AA: ninguna infracción detectada en la vista comprobada.

Las capturas verifican el HTML en Chrome. No constituyen una prueba de recepción real en Gmail u Outlook; cada cliente puede ajustar fuentes, esquinas y colores en modo oscuro.
