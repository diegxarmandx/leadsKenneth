import { expect, test } from "@playwright/test";
import { ApiError, requestJson } from "../../src/lib/api";

test("cancellation while reading a 200 response body reaches the effect's catch", async () => {
  const originalFetch = globalThis.fetch;
  const controller = new AbortController();
  let reading!: () => void;
  const bodyStarted = new Promise<void>((resolve) => {
    reading = resolve;
  });
  globalThis.fetch = async () =>
    new Response(
      new ReadableStream({
        start(stream) {
          stream.enqueue(new TextEncoder().encode('{"status":'));
          controller.signal.addEventListener(
            "abort",
            () => stream.error(controller.signal.reason),
            { once: true },
          );
        },
        pull() {
          reading();
        },
      }),
      { status: 200 },
    );
  try {
    const result = requestJson("http://localhost/order", {
      signal: controller.signal,
    });
    // Attach the rejection handler before triggering cleanup, just as the effect does.
    const handled = expect(result).rejects.toMatchObject({
      name: "AbortError",
    });
    await bodyStarted;
    controller.abort();
    await handled;
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("genuine response stream failures are not converted to successful null responses", async () => {
  const originalFetch = globalThis.fetch;
  const failure = new TypeError("Response stream disconnected");
  globalThis.fetch = async () =>
    new Response(
      new ReadableStream({
        start(stream) {
          stream.error(failure);
        },
      }),
      { status: 200 },
    );
  try {
    await expect(requestJson("http://localhost/order")).rejects.toBe(failure);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("HTTP API failures retain their status and error message", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () =>
    Response.json({ error: { code: "connection_failed" } }, { status: 503 });
  try {
    await expect(requestJson("http://localhost/order")).rejects.toMatchObject({
      name: "ApiError",
      status: 503,
      code: "connection_failed",
    } satisfies Partial<ApiError>);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
