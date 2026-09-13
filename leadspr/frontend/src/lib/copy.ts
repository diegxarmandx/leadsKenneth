// Presentation-only Spanish copy. Backend codes and domain values stay unchanged.
const errors: Record<string, string> = {
  insufficient_inventory:
    "No hay suficientes leads disponibles para completar esta cantidad. Actualizamos el inventario; revisa tu selección.",
  pricing_rule_not_found:
    "El precio cambió. Revisa los precios actualizados antes de continuar al pago.",
  pricing_rule_conflict:
    "Ese precio ya está asignado a otro rango de antigüedad. Usa un precio distinto para mantener los cuatro tipos de leads separados.",
  invalid_price:
    "Ingresa un precio mayor de cero con un máximo de dos decimales.",
  invalid_passcode: "Contraseña incorrecta. Intenta nuevamente.",
  session_expired: "Tu sesión terminó. Ingresa tu contraseña para continuar.",
  admin_not_configured:
    "El acceso administrativo no está configurado. Comunícate con la persona a cargo de la demostración.",
  invalid_origin:
    "Esta solicitud debe hacerse desde la aplicación de demostración.",
  test_mode_required:
    "Esta demostración requiere el modo de prueba de Stripe. El pago no está disponible en este momento.",
  invalid_checkout:
    "No se pudo iniciar un pago de prueba verificado. Intenta nuevamente.",
  sheet_sync_failed:
    "No se pudo sincronizar la hoja de Google Sheets. Revisa la hoja e intenta nuevamente.",
  sync_in_progress:
    "Ya hay una sincronización en progreso. Espera un momento e intenta nuevamente.",
  connection_failed:
    "No pudimos conectar con el servicio. Revisa tu conexión e intenta nuevamente.",
};

export function apiErrorCopy(
  code: string,
  status: number,
  path: string,
): string {
  if (errors[code]) return errors[code];
  if (status === 401) return errors.session_expired;
  if (path.includes("pricing-rules"))
    return status === 422
      ? errors.invalid_price
      : "No se pudo actualizar el precio. Intenta nuevamente.";
  if (path.includes("inventory"))
    return "No se pudo cargar el inventario. Intenta nuevamente.";
  if (path.includes("/sync")) return errors.sheet_sync_failed;
  if (path.includes("/checkout"))
    return status === 422
      ? "Revisa los datos de contacto y la cantidad antes de continuar."
      : "No se pudo iniciar el proceso de pago. Intenta nuevamente.";
  if (path.includes("/purchases"))
    return "No se pudo consultar la orden. Revisa el enlace e intenta nuevamente.";
  return "No se pudo completar la solicitud. Intenta nuevamente.";
}
