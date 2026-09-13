import { NextResponse } from "next/server";
import {
  createSession,
  SESSION_COOKIE,
  SESSION_SECONDS,
} from "@/lib/server/admin-session";
import {
  BackendError,
  errorResponse,
  requireSameOrigin,
} from "@/lib/server/backend";

export async function POST(request: Request) {
  try {
    requireSameOrigin(request);
    const input: unknown = await request.json();
    if (
      !input ||
      typeof input !== "object" ||
      !("passcode" in input) ||
      typeof input.passcode !== "string" ||
      input.passcode.length > 256
    )
      throw new BackendError(
        400,
        "invalid_input",
        "Ingresa tu contraseña de administración.",
      );
    const session = createSession(input.passcode);
    const response = NextResponse.json(
      { authenticated: true },
      { headers: { "Cache-Control": "no-store" } },
    );
    response.cookies.set(SESSION_COOKIE, session, {
      httpOnly: true,
      secure: new URL(request.url).protocol === "https:",
      sameSite: "strict",
      path: "/",
      maxAge: SESSION_SECONDS,
    });
    return response;
  } catch (error) {
    return errorResponse(error);
  }
}

export async function DELETE(request: Request) {
  try {
    requireSameOrigin(request);
    const response = NextResponse.json({ authenticated: false });
    response.cookies.set(SESSION_COOKIE, "", {
      httpOnly: true,
      sameSite: "strict",
      path: "/",
      maxAge: 0,
    });
    return response;
  } catch (error) {
    return errorResponse(error);
  }
}
