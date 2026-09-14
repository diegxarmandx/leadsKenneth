import { requireAdminSession } from "@/lib/server/admin-session";
import {
  backendRequest,
  BackendError,
  errorResponse,
  requireSameOrigin,
} from "@/lib/server/backend";
import type { LeadEntryResponse } from "@/types/api";

export const maxDuration = 180;

export async function POST(request: Request) {
  try {
    requireSameOrigin(request);
    await requireAdminSession();
    const key = request.headers.get("Idempotency-Key");
    if (
      !key ||
      !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
        key,
      )
    )
      throw new BackendError(
        422,
        "invalid_lead",
        "No se pudo identificar el envío. Abre el formulario nuevamente.",
      );
    const data: unknown = await request.json();
    if (
      !data ||
      typeof data !== "object" ||
      Array.isArray(data) ||
      Object.keys(data).some(
        (key) =>
          ![
            "first_name",
            "last_name",
            "phone",
            "email",
            "municipality",
            "lead_date",
          ].includes(key),
      )
    )
      throw new BackendError(
        422,
        "invalid_lead",
        "Revisa los datos del lead e intenta nuevamente.",
      );
    return Response.json(
      await backendRequest<LeadEntryResponse>(
        "/admin/leads",
        {
          method: "POST",
          headers: { "Idempotency-Key": key },
          body: JSON.stringify(data),
          signal: AbortSignal.timeout(175_000),
        },
        true,
      ),
      { status: 201, headers: { "Cache-Control": "no-store" } },
    );
  } catch (error) {
    return errorResponse(error);
  }
}
