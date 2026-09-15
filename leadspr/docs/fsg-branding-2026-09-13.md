# Identidad FSG — entrega del 13 de septiembre de 2026

## Información verificada

Fuente única de información pública: https://fsgwebsite.azurewebsites.net/, inspeccionada antes de editar mediante HTML, contenido renderizado en Chrome y sus propios recursos públicos. No se utilizaron empresas FSG de otros países.

- Marca pública: **FSG Seguros**. Nombre corporativo y texto del logo: **Financial Support Group Inc.**
- Posicionamiento: asesoría en seguros en Puerto Rico; orientación gratuita, evaluación de alternativas de múltiples aseguradoras y acompañamiento en reclamaciones.
- Mensaje de portada del sitio: la familia y la protección compartida. Se adaptó a texto original en español, sin atribuir el nuevo titular a una cita oficial.
- Cuatro productos publicados: **8 Seguros en 1**, **Seguro de Cáncer**, **Gastos Finales**, **Retiro y Ahorro**. La protección de vida se representa en Gastos Finales y en el marketplace existente. No se añadieron líneas de seguros no verificadas.
- Teléfono: **787-658-6122**. WhatsApp: **787-233-4871**.
- Correo: **0ffice@fsgseguros.com**, con cero inicial, exactamente como aparece en el enlace del sitio.
- Dirección: **10000 Carr. 2, Barrio Cocos, Quebradillas, Puerto Rico 00678**.
- Horario: **lunes a viernes, 8:30 a. m. – 5:30 p. m.**
- Redes: https://facebook.com/segurosfsg y https://instagram.com/fsg_seguros. Se verificaron como enlaces publicados por el sitio del cliente; no se consultaron empresas homónimas.
- Identidad visual de la fuente: verdes oliva/lima, acentos oscuros, logo con árbol y figura humana, tipografía Inter y fotos del equipo. El tema HTML declara `#9EBB35`.

## Cambios entregados

1. **Inicio:** nueva portada centrada en orientación al consumidor; cuatro servicios, sección del equipo, acceso al marketplace de agentes y contacto. Toda la interfaz conserva español y `lang="es-PR"`.
2. **Marca:** FSG Seguros en navegación, pie, administración, acceso administrativo, estado/cancelación de pago y página no encontrada. «Operaciones FSG» y «Marketplace de Leads para Agentes» identifican las páginas operacionales.
3. **Fotos:** `frontend/public/images/fsg/equipo-fsg.jpg` es el original del equipo compartido por el cliente, usado en el hero. `equipo-certificaciones.jpeg` es la versión publicada por el mismo cliente en `/images/banner-2.jpeg`, usada en «Conoce a FSG». Esta última versión mide 1080 × 1098, más corta que el arte mostrado en el chat; se presenta completa tal como la sirve el sitio. Ambas usan `next/image`, tamaños responsivos y proporciones originales. No se editaron personas. Se retiró la foto genérica `family.jpg`, ya sin referencias.
4. **Logo:** archivo oficial recibido e integrado como `frontend/public/images/fsg/logo-fsg.jpg` en navegación y pie compartidos, reemplazando el nombre provisional en texto. También se usa como icono de navegador y Apple. Se preservó el original sin editar.
5. **Contacto:** enlaces funcionales `tel:`, `mailto:`, WhatsApp y redes. No se creó otro formulario ni se enviaron mensajes a terceros.
6. **Tema:** fondo crema conservado; verde bosque en marca, títulos y botones, oliva en detalles de la portada. Las tarjetas siguen azul marino; tablas y formularios conservan contraste, y Editar sigue dorado.
7. **Metadatos:** títulos, descripciones, nombre de aplicación y Open Graph con FSG y localización `es_PR`. Se conserva `noindex` para el MVP. El icono usa el logo oficial; la imagen social definitiva puede configurarse al confirmar el dominio de despliegue. No se inventó un dominio canónico.
8. **Stripe:** único cambio en código backend: nombre visible del producto para nuevas sesiones, «FSG Seguros · Leads de seguro de vida». Contratos, montos, metadata de órdenes, inventario, esquemas y lógica de pagos permanecen intactos.

## Archivos

- `frontend/src/app/page.tsx`, `home.module.css`, `globals.css`: portada y presentación.
- `frontend/src/lib/company.ts`: datos públicos verificados y enlaces de contacto.
- `frontend/src/components/brand.tsx`, `navbar.tsx`, `footer.tsx`: identidad compartida.
- `frontend/src/app/layout.tsx`, `leads/page.tsx`, `admin/page.tsx`: metadatos.
- `frontend/src/app/not-found.tsx`, `checkout/cancel/page.tsx`, `components/marketplace/order-status.tsx`: mensajes FSG.
- `frontend/src/components/marketplace/marketplace.tsx`, `operations/dashboard.tsx`, `operations/admin-sign-in.tsx`: títulos y textos.
- `frontend/public/images/fsg/`: fotos y guía para el logo. Se eliminó `frontend/public/images/family.jpg`.
- `backend/app/integrations/stripe/client.py`, `backend/tests/test_integrations.py`: nombre visible de Stripe y su prueba.
- `frontend/tests/e2e/demo.spec.ts`, `branding.spec.ts`: expectativas actualizadas y verificación de identidad, contactos y fotos.
- `README.md`, `frontend/README.md` y este informe: documentación.

## Validación

- Frontend: lint, TypeScript, formato Prettier y build de producción satisfactorios.
- Backend: Ruff satisfactorio; **111 pruebas aprobadas**. Dos advertencias de deprecación existentes de Starlette/AnyIO.
- Chrome/Playwright: **24 pruebas aprobadas**. Incluyen navegación, accesibilidad Axe, inventario, precios, autenticación, Añadir Lead, sincronización, checkout, fulfillment y manejo de errores reales.
- Las pruebas de cancelación confirman que cambios de municipio, polling, salida de la página y regreso desde checkout no producen AbortError/unhandledRejection sin manejar.
- La nueva prueba verifica los contactos, ausencia de marca antigua en contenido estático, metadatos FSG, fotos cargadas sin distorsión y ausencia de desbordamiento a 320, 768 y 1440 px.
- Revisión visual adicional con el backend local existente: inicio a 1440 y 390 px; leads con Salinas; administración autenticada en escritorio y móvil, incluido el formulario Añadir Lead abierto. Sin errores JavaScript observados. No se crearon leads, compras ni cambios de precios en datos reales para esta tarea.
- Las escrituras y checkout de las pruebas E2E usan datos y servicios aislados. Esta entrega no realizó un nuevo pago real/test contra Stripe ni una nueva escritura en la hoja del cliente.

## Contenido pendiente y revisión antes del lunes

- Logo oficial integrado: revisar su tamaño y legibilidad en navegación, pie de página e icono del navegador. El JPEG recibido tiene fondo blanco; no se fabricaron variantes del logo.
- Confirmar con el cliente que el correo con cero inicial es intencional; la aplicación respeta lo publicado actualmente.
- Revisar en un teléfono la portada, ambas fotos y los accesos de contacto. Confirmar aprobación editorial del texto adaptado y de los cuatro servicios.
- Se conservaron los avisos MODO DEMO y Stripe de prueba; el pie los limita explícitamente al marketplace. Los datos operacionales siguen siendo de demostración.
- La búsqueda de marca antigua en código deja solo claves internas de cookie/firma/sessionStorage y pruebas de regresión. No se renombraron para evitar invalidar sesiones u órdenes.
- En la base de datos existente, una compra histórica conserva el nombre del comprador «Borinquen Demo Agent». Es dato histórico recibido del backend, no marca de la aplicación; no se alteró ni se ocultó. Las sesiones antiguas de Stripe también conservan el texto con el que se crearon.
- No se añadieron estadísticas, testimonios, nombres de empleados, aseguradoras específicas, licencias ni garantías de beneficios. Aunque el sitio publica algunas cifras, no son necesarias para esta portada. No se verificó entregabilidad del correo ni atención de los números por medio de mensajes o llamadas.

### Verificación del logo recibido

Logo oficial integrado después de la entrega inicial. Lint y build (incluido TypeScript) aprobados; las dos pruebas existentes de identidad y navegación/accesibilidad responsiva pasaron. Se inspeccionaron encabezado y pie a 1440 y 390 px: ambos logos cargan, el símbolo y el nombre se ven completos y no se observaron errores JavaScript.
