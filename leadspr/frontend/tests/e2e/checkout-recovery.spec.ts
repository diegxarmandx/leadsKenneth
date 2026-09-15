import { expect, test } from "@playwright/test";

const fixture = "http://127.0.0.1:4319/__test";
const statusUrl = "/checkout/success?order_id=ORD-TEST0002";

test.beforeEach(async ({ request }) => {
  await request.post(`${fixture}/reset`);
});

test("return from checkout recovers a paid order and stops polling after email acceptance", async ({
  page,
  request,
}) => {
  await request.post(`${fixture}/state`, { data: { reconcilePaid: true } });
  let requests = 0;
  page.on("request", (req) => {
    if (req.url().includes("/purchases/")) requests++;
  });
  await page.goto(statusUrl);
  await expect(
    page.getByRole("heading", { name: "Tu orden está completada." }),
  ).toBeVisible();
  await expect(page.locator(".email-confirmation")).toContainText(
    "Enviamos el correo",
  );
  const count = requests;
  await page.waitForTimeout(2500);
  expect(requests).toBe(count);
  await page.reload();
  await expect(page.locator(".email-confirmation")).toContainText(
    "Enviamos el correo",
  );
  const state = await (await request.get(`${fixture}/state`)).json();
  expect(state.reconciliationCount).toBe(1);
});

test("pending orders stop automatic polling with an actionable message", async ({
  page,
}) => {
  await page.clock.install();
  let refreshes = 0;
  page.on("response", (res) => {
    if (res.url().endsWith("/ORD-TEST0002/refresh")) refreshes++;
  });
  await page.goto(statusUrl);
  await expect.poll(() => refreshes).toBe(1);
  for (let count = 2; count <= 12; count++) {
    await page.clock.runFor(10000);
    await expect.poll(() => refreshes).toBe(count);
  }
  await expect(page.getByRole("status")).toContainText(
    "Pausamos las consultas automáticas",
  );
  await page.clock.runFor(60000);
  expect(refreshes).toBe(12);
  await page.getByRole("button", { name: "Actualizar estado" }).click();
  await expect.poll(() => refreshes).toBe(13);
});

test("reconciliation proxy rejects other origins and does not trust browser payment details", async ({
  request,
}) => {
  const url = "/api/marketplace/purchases/ORD-TEST0002/refresh";
  expect((await request.post(url)).status()).toBe(403);
  expect(
    (
      await request.post(url, { headers: { Origin: "https://other.example" } })
    ).status(),
  ).toBe(403);
  const response = await request.post(url, {
    headers: { Origin: "http://localhost:4318" },
    data: {
      payment_status: "paid",
      status: "FULFILLED",
      checkout_id: "cs_fake",
    },
  });
  expect(response.status()).toBe(200);
  expect((await response.json()).status).toBe("PENDING");
});

for (const [code, message] of [
  ["email_delivery_pending", "el envío del correo falló"],
  ["email_delivery_blocked", "Administración debe revisar"],
]) {
  test(`email state ${code} preserves fulfillment and displays the required action`, async ({
    page,
    request,
  }) => {
    await page.route(
      "**/api/marketplace/purchases/ORD-TEST0002/refresh",
      async (route) => {
        await request.post(`${fixture}/state`, {
          data: { orderStatus: "FULFILLED", emailPending: true },
        });
        await route.fulfill({
          status: 502,
          json: { error: { code } },
        });
      },
    );
    await page.goto(statusUrl);
    await expect(
      page.getByRole("heading", { name: "Tu orden está completada." }),
    ).toBeVisible();
    await expect(page.locator("main").getByRole("alert")).toContainText(
      message,
    );
    await expect(page.locator(".email-confirmation")).toContainText(
      "pendiente",
    );
    await request.post(`${fixture}/state`, { data: { emailPending: false } });
    await page.getByRole("button", { name: "Actualizar estado" }).click();
    await expect(page.locator(".email-confirmation")).toContainText(
      "Enviamos el correo",
    );
    await expect(page.locator("main").getByRole("alert")).toHaveCount(0);
  });
}
