import {
  backendRequest,
  BackendError,
  errorResponse,
  requireSameOrigin,
} from "@/lib/server/backend";
import type { CheckoutConfig, CheckoutResponse } from "@/types/api";

type Context = { params: Promise<{ path: string[] }> };
export const maxDuration = 120;

export async function GET(request: Request, context: Context) {
  try {
    const path = (await context.params).path.join("/");
    const allowed =
      [
        "inventory/summary",
        "inventory/municipalities",
        "checkout/config",
      ].includes(path) || /^purchases\/ORD-[A-Z0-9-]{6,40}$/.test(path);
    if (!allowed)
      throw new BackendError(404, "not_found", "Página no encontrada.");
    const query = new URLSearchParams();
    const input = new URL(request.url).searchParams;
    for (const key of ["municipality", "insurance_type", "scope"]) {
      const value = input.get(key);
      if (value) query.set(key, value);
    }
    return Response.json(
      await backendRequest(`/${path}${query.size ? `?${query}` : ""}`),
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch (error) {
    return errorResponse(error);
  }
}

export async function POST(request: Request, context: Context) {
  try {
    requireSameOrigin(request);
    if ((await context.params).path.join("/") !== "checkout")
      throw new BackendError(404, "not_found", "Página no encontrada.");
    const config = await backendRequest<CheckoutConfig>("/checkout/config");
    if (config.payment_mode !== "test")
      throw new BackendError(
        409,
        "test_mode_required",
        "Esta demostración requiere el modo de prueba de Stripe. El pago no está disponible en este momento.",
      );
    const data: unknown = await request.json();
    const checkout = await backendRequest<CheckoutResponse>("/checkout", {
      method: "POST",
      body: JSON.stringify(data),
    });
    const destination = new URL(checkout.checkout_url);
    if (
      destination.protocol !== "https:" ||
      destination.hostname !== "checkout.stripe.com" ||
      !checkout.checkout_session_id.startsWith("cs_test_")
    )
      throw new BackendError(
        502,
        "invalid_checkout",
        "No pudimos abrir un pago de prueba verificado de Stripe. Intenta nuevamente.",
      );
    return Response.json(checkout, {
      status: 201,
      headers: { "Cache-Control": "no-store" },
    });
  } catch (error) {
    return errorResponse(error);
  }
}
