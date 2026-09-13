import { requireAdminSession } from "@/lib/server/admin-session";
import {
  backendRequest,
  BackendError,
  errorResponse,
  requireSameOrigin,
} from "@/lib/server/backend";
import type { PricingRule } from "@/types/api";

export async function PATCH(
  request: Request,
  context: { params: Promise<{ id: string }> },
) {
  try {
    requireSameOrigin(request);
    await requireAdminSession();
    const { id } = await context.params;
    const data: unknown = await request.json();
    // The demo editor permits price changes only, never range/exclusion changes.
    if (
      !/^[1-9]\d*$/.test(id) ||
      !data ||
      typeof data !== "object" ||
      Object.keys(data).length !== 1 ||
      !("price_cents" in data) ||
      typeof data.price_cents !== "number" ||
      !Number.isSafeInteger(data.price_cents) ||
      data.price_cents <= 0
    ) {
      throw new BackendError(
        422,
        "invalid_price",
        "Ingresa un precio mayor de cero con un máximo de dos decimales.",
      );
    }
    return Response.json(
      await backendRequest<PricingRule>(
        `/admin/pricing-rules/${id}`,
        {
          method: "PATCH",
          body: JSON.stringify({ price_cents: data.price_cents }),
        },
        true,
      ),
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch (error) {
    return errorResponse(error);
  }
}
