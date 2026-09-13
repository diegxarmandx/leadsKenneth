import { requireAdminSession } from "@/lib/server/admin-session";
import { backendRequest, errorResponse } from "@/lib/server/backend";
import type { DashboardData } from "@/types/api";

export async function GET() {
  try {
    await requireAdminSession();
    return Response.json(
      await backendRequest<DashboardData>("/admin/dashboard", {}, true),
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch (error) {
    return errorResponse(error);
  }
}
