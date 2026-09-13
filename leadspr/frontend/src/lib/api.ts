import { apiErrorCopy } from "@/lib/copy";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function requestJson<T>(
  url: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  let response: Response;
  try {
    response = await fetch(url, {
      ...init,
      headers,
      cache: "no-store",
      credentials: "same-origin",
      signal: init.signal ?? AbortSignal.timeout(30_000),
    });
  } catch (error) {
    if (init.signal?.aborted) throw error;
    throw new ApiError(
      503,
      "connection_failed",
      "No pudimos conectar con el servicio. Revisa tu conexión e intenta nuevamente.",
    );
  }
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const error =
      body && typeof body === "object" && "error" in body ? body.error : null;
    const code =
      error &&
      typeof error === "object" &&
      "code" in error &&
      typeof error.code === "string"
        ? error.code
        : "request_failed";
    throw new ApiError(
      response.status,
      code,
      apiErrorCopy(code, response.status, url),
    );
  }
  return body as T;
}

export function apiRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  return requestJson<T>(`/api/marketplace${path}`, init);
}

export function errorMessage(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : "No se pudo completar la operación. Intenta nuevamente.";
}
