import { requireAdminSession } from "@/lib/server/admin-session";
import {
  backendRequest,
  errorResponse,
  requireSameOrigin,
} from "@/lib/server/backend";
import type { SyncRun } from "@/types/api";

export const maxDuration = 120;

export async function POST(request: Request) {
  try {
    requireSameOrigin(request);
    await requireAdminSession();
    return Response.json(
      await backendRequest<SyncRun>(
        "/admin/sync",
        { method: "POST", signal: AbortSignal.timeout(115_000) },
        true,
      ),
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch (error) {
    return errorResponse(error);
  }
}
