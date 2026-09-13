import "server-only";
import {
  createHmac,
  randomBytes,
  timingSafeEqual,
  createHash,
} from "node:crypto";
import { cookies } from "next/headers";
import { BackendError } from "@/lib/server/backend";

export const SESSION_COOKIE = "borinquen_operations";
export const SESSION_SECONDS = 8 * 60 * 60;

function signingKey(): string {
  const key = process.env.ADMIN_API_TOKEN;
  if (!key || key.length < 32)
    throw new BackendError(
      503,
      "admin_not_configured",
      "El acceso administrativo no está configurado. Comunícate con la persona a cargo de la demostración.",
    );
  return key;
}

function signature(payload: string): string {
  return createHmac("sha256", signingKey())
    .update(`borinquen-demo-session:${payload}`)
    .digest("base64url");
}

export function createSession(passcode: string): string {
  const expected = process.env.DEMO_ADMIN_PASSWORD;
  if (!expected || expected.length < 12)
    throw new BackendError(
      503,
      "admin_not_configured",
      "El acceso administrativo no está configurado. Comunícate con la persona a cargo de la demostración.",
    );
  const digest = (value: string) => createHash("sha256").update(value).digest();
  if (!timingSafeEqual(digest(passcode), digest(expected)))
    throw new BackendError(
      401,
      "invalid_passcode",
      "Contraseña incorrecta. Intenta nuevamente.",
    );
  const payload = Buffer.from(
    JSON.stringify({
      expires: Date.now() + SESSION_SECONDS * 1000,
      nonce: randomBytes(16).toString("hex"),
    }),
  ).toString("base64url");
  return `${payload}.${signature(payload)}`;
}

export async function hasAdminSession(): Promise<boolean> {
  const value = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!value || value.length > 1024) return false;
  try {
    const [payload, supplied, extra] = value.split(".");
    if (!payload || !supplied || extra) return false;
    const expected = signature(payload);
    if (
      supplied.length !== expected.length ||
      !timingSafeEqual(Buffer.from(supplied), Buffer.from(expected))
    )
      return false;
    const decoded: unknown = JSON.parse(
      Buffer.from(payload, "base64url").toString(),
    );
    return (
      !!decoded &&
      typeof decoded === "object" &&
      "expires" in decoded &&
      typeof decoded.expires === "number" &&
      decoded.expires > Date.now()
    );
  } catch {
    return false;
  }
}

export async function requireAdminSession(): Promise<void> {
  if (!(await hasAdminSession()))
    throw new BackendError(
      401,
      "session_expired",
      "Tu sesión terminó. Ingresa tu contraseña para continuar.",
    );
}
