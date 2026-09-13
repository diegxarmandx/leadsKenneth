import "server-only";

export class BackendError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

export async function backendRequest<T>(
  path: string,
  init: RequestInit = {},
  admin = false,
): Promise<T> {
  const base = (
    process.env.BACKEND_API_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://127.0.0.1:8000/api/v1"
  ).replace(/\/$/, "");
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body) headers.set("Content-Type", "application/json");
  if (admin) {
    const token = process.env.ADMIN_API_TOKEN;
    if (!token || token.length < 32)
      throw new BackendError(
        503,
        "admin_not_configured",
        "El acceso administrativo no está configurado. Comunícate con la persona a cargo de la demostración.",
      );
    headers.set("Authorization", `Bearer ${token}`);
  }
  let response: Response;
  try {
    response = await fetch(`${base}${path}`, {
      ...init,
      headers,
      cache: "no-store",
      signal: init.signal ?? AbortSignal.timeout(90_000),
    });
  } catch {
    throw new BackendError(
      503,
      "service_unavailable",
      "No pudimos conectar con el servicio. Intenta nuevamente en unos minutos.",
    );
  }
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const error =
      body && typeof body === "object" && "error" in body ? body.error : null;
    const message =
      error &&
      typeof error === "object" &&
      "message" in error &&
      typeof error.message === "string"
        ? error.message
        : "No se pudo completar la solicitud. Intenta nuevamente.";
    const code =
      error &&
      typeof error === "object" &&
      "code" in error &&
      typeof error.code === "string"
        ? error.code
        : "request_failed";
    throw new BackendError(response.status, code, message);
  }
  return body as T;
}

export function errorResponse(error: unknown): Response {
  const known = error instanceof BackendError;
  return Response.json(
    {
      error: {
        code: known ? error.code : "request_failed",
        message: known
          ? error.message
          : "No se pudo completar la solicitud. Intenta nuevamente.",
      },
    },
    {
      status: known ? error.status : 500,
      headers: { "Cache-Control": "no-store" },
    },
  );
}

export function requireSameOrigin(request: Request): void {
  const origin = request.headers.get("origin");
  if (!origin || origin !== new URL(request.url).origin)
    throw new BackendError(
      403,
      "invalid_origin",
      "Esta solicitud debe hacerse desde la aplicación de demostración.",
    );
}
