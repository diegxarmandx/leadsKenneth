import { expect, test, type Page } from "@playwright/test";

const fixture = "http://127.0.0.1:4319/__test";
const statusUrl = "/checkout/success?order_id=ORD-TEST0002";

async function monitorRejections(page: Page) {
  const errors: string[] = [];
  const cancellations: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (/AbortError|unhandledRejection|unhandledrejection/.test(message.text()))
      errors.push(message.text());
  });
  page.on("requestfailed", (request) => {
    if (
      request.url().includes("/api/marketplace/") &&
      request.failure()?.errorText.includes("ERR_ABORTED")
    )
      cancellations.push(request.url());
  });
  await page.addInitScript(() => {
    window.addEventListener("unhandledrejection", (event) => {
      // Observe without preventing the browser's normal error reporting.
      console.error("unhandledrejection", String(event.reason));
    });
  });
  return { errors, cancellations };
}

async function expectInventory(page: Page) {
  await expect(
    page.getByRole("radio", { name: /^Leads Recientes/ }),
  ).toBeChecked();
}

test.beforeEach(async ({ request }) => {
  await request.post(`${fixture}/reset`);
});

test("municipality changes and navigation cancel inventory without unhandled rejections", async ({
  page,
  request,
}) => {
  const observed = await monitorRejections(page);
  await page.goto(statusUrl);
  await expect(page.locator(".order-result-details")).toBeVisible();
  await page.getByRole("link", { name: "Volver al Marketplace" }).click();
  await expectInventory(page);
  await request.post(`${fixture}/state`, { data: { inventoryDelay: 1500 } });
  const firstRequest = page.waitForRequest(
    /inventory\/summary\?municipality=Salinas/,
  );
  await page.getByLabel("Municipio", { exact: true }).selectOption("Salinas");
  await firstRequest;
  const nextRequest = page.waitForRequest(
    /inventory\/summary\?municipality=San\+Juan/,
  );
  await page.getByLabel("Municipio", { exact: true }).selectOption("San Juan");
  await nextRequest;
  await page.goBack();
  await expect(page).toHaveURL(/checkout\/success/);
  await expect(page.locator(".order-result-details")).toBeVisible();
  await expect
    .poll(() => observed.cancellations.length)
    .toBeGreaterThanOrEqual(2);
  await request.post(`${fixture}/state`, { data: { inventoryDelay: 0 } });
  await page.getByRole("link", { name: "Volver al Marketplace" }).click();
  await expectInventory(page);
  await page.waitForTimeout(1700); // Let the cancelled upstream requests settle.
  expect(observed.errors).toEqual([]);
});

test("polling refresh and unmount cancel requests and clear pending timers", async ({
  page,
  request,
}) => {
  const observed = await monitorRejections(page);
  let purchases = 0;
  page.on("request", (req) => {
    if (req.url().includes("/api/marketplace/purchases/")) purchases += 1;
  });
  await page.goto(statusUrl);
  await expect(page.locator(".order-result-details")).toBeVisible();
  await request.post(`${fixture}/state`, { data: { purchaseDelay: 1500 } });
  await page.waitForRequest(/\/api\/marketplace\/purchases\//);
  const refreshRequest = page.waitForRequest(/\/api\/marketplace\/purchases\//);
  await page.getByRole("button", { name: "Actualizar estado" }).click();
  await refreshRequest;
  await page.getByRole("link", { name: "Volver al Marketplace" }).click();
  await expectInventory(page);
  await expect
    .poll(() => observed.cancellations.length)
    .toBeGreaterThanOrEqual(2);
  const afterUnmount = purchases;
  await page.waitForTimeout(2300);
  expect(purchases).toBe(afterUnmount);
  await request.post(`${fixture}/state`, { data: { purchaseDelay: 0 } });
  await page.goBack();
  await expect(page.locator(".order-result-details")).toBeVisible();
  await page.getByRole("link", { name: "Volver al Marketplace" }).click();
  await expectInventory(page);
  const afterTimerCleanup = purchases;
  await page.waitForTimeout(2300);
  expect(purchases).toBe(afterTimerCleanup);
  expect(observed.errors).toEqual([]);
});

test("checkout return and repeated navigation preserve successful responses", async ({
  page,
}) => {
  const observed = await monitorRejections(page);
  await page.route("https://checkout.stripe.com/**", (route) =>
    route.fulfill({ contentType: "text/html", body: "<h1>Test checkout</h1>" }),
  );
  await page.goto("/leads");
  await expectInventory(page);
  await page.getByLabel("Nombre completo").fill("Cancellation Test");
  await page.getByLabel("Correo electrónico").fill("test@example.com");
  await page.getByRole("button", { name: "Continuar al Pago Seguro" }).click();
  await expect(page).toHaveURL(
    "https://checkout.stripe.com/c/pay/cs_test_fixture",
  );
  await page.goto(statusUrl);
  for (let i = 0; i < 3; i += 1) {
    await expect(page.locator(".order-result-details")).toBeVisible();
    await page.getByRole("link", { name: "Volver al Marketplace" }).click();
    await expectInventory(page);
    await page.goBack();
  }
  await page.getByRole("link", { name: "Volver al Marketplace" }).click();
  await expectInventory(page);
  expect(observed.errors).toEqual([]);
});

test("genuine network and polling API failures remain visible and retryable", async ({
  page,
  request,
}) => {
  const observed = await monitorRejections(page);
  await page.route("**/api/marketplace/inventory/summary*", (route) =>
    route.abort("failed"),
  );
  await page.goto("/leads");
  await expect(page.locator("main").getByRole("alert")).toContainText(
    "No pudimos conectar con el servicio",
  );
  await page.unroute("**/api/marketplace/inventory/summary*");
  await page.getByRole("button", { name: "Intenta nuevamente" }).click();
  await expectInventory(page);
  await page.goto(statusUrl);
  await expect(page.locator(".order-result-details")).toBeVisible();
  await request.post(`${fixture}/state`, { data: { purchaseError: true } });
  await expect(page.locator("main").getByRole("alert")).toContainText(
    "No se pudo consultar la orden",
  );
  await request.post(`${fixture}/state`, {
    data: { purchaseError: false, orderStatus: "FULFILLED" },
  });
  await page.getByRole("button", { name: "Actualizar estado" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Tu orden está completada.",
  );
  await expect(page.locator("main").getByRole("alert")).toHaveCount(0);
  expect(observed.errors).toEqual([]);
});
