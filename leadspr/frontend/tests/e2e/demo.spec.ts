import {
  expect,
  test,
  type APIRequestContext,
  type Page,
} from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const fixture = "http://127.0.0.1:4319/__test";
const origin = "http://localhost:4318";
const checkout = {
  buyer_name: "Demo Agent",
  buyer_email: "agent@example.com",
  municipality: "Salinas",
  insurance_type: "Life Insurance",
  quantity: 2,
  price_per_lead_cents: 2100,
};
async function configure(
  request: APIRequestContext,
  data: Record<string, unknown>,
) {
  await request.post(`${fixture}/state`, { data });
}
async function signIn(page: Page) {
  await page.goto("/admin");
  await page.getByLabel("Contraseña").fill("automated-test-passcode");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(
    page.getByRole("heading", { name: "Leads Activos", exact: true }),
  ).toBeVisible();
}
async function chooseLeads(page: Page) {
  await page.goto("/leads");
  await expect(
    page.getByRole("radio", { name: /^Leads Recientes/ }),
  ).toBeChecked();
  await page.getByLabel("Municipio", { exact: true }).selectOption("Salinas");
  await expect(
    page.getByRole("radio", { name: /Leads Recientes.*5 disponibles/ }),
  ).toBeChecked();
  await page.getByRole("spinbutton").fill("2");
  await page.getByLabel("Nombre completo").fill("Demo Agent");
  await page.getByLabel("Correo electrónico").fill("agent@example.com");
}
test.beforeEach(async ({ request }) => {
  await request.post(`${fixture}/reset`);
});

test("navigation, responsive layout, and accessible pages", async ({
  page,
}) => {
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      "Protegiendo a las familias de Puerto Rico para lo que viene",
    );
    for (const path of ["/", "/leads", "/admin"]) {
      await page.goto(path);
      if (path === "/leads")
        await expect(
          page.getByRole("radio", { name: /^Leads Recientes/ }),
        ).toBeChecked();
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth,
        ),
      ).toBe(true);
      const report = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze();
      expect(
        report.violations.map((v) => ({
          id: v.id,
          nodes: v.nodes.map((n) => ({
            target: n.target,
            summary: n.failureSummary,
          })),
        })),
      ).toEqual([]);
    }
    await page
      .getByRole("navigation", { name: "Navegación principal" })
      .getByRole("link", { name: "Inicio", exact: true })
      .click();
    await page
      .getByRole("link", { name: "Explorar Leads para Agentes", exact: true })
      .click();
    await expect(page).toHaveURL(/\/leads$/);
    await expect(
      page
        .getByRole("navigation")
        .getByRole("link", { name: "Leads para Agentes" }),
    ).toHaveAttribute("aria-current", "page");
  }
  await page.goto("/buy");
  await expect(page).toHaveURL(/\/leads$/);
});

test("backend prices, stock limits, empty tiers, and live totals", async ({
  page,
}) => {
  await chooseLeads(page);
  await expect(page.locator(".summary-total")).toContainText("$42.00");
  await page.getByRole("button", { name: "Aumentar cantidad" }).click();
  await expect(page.locator(".summary-total")).toContainText("$63.00");
  await page.getByRole("spinbutton").fill("6");
  await expect(
    page.getByText("Ingresa un número entero del 1 al 5."),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Continuar al Pago Seguro" }),
  ).toBeDisabled();
  await expect(
    page.getByRole("radio", { name: /^Leads Antiguos/ }),
  ).toBeDisabled();
  await page.getByRole("spinbutton").fill("5");
  await page.getByLabel("Municipio", { exact: true }).selectOption("San Juan");
  await expect(
    page.getByRole("radio", { name: /^Leads Nuevos/ }),
  ).toBeChecked();
  await expect(page.getByRole("spinbutton")).toHaveValue("3");
  await expect(page.locator(".summary-total")).toContainText("$90.00");
});

test("inventory failures retry without invented stock", async ({
  page,
  request,
}) => {
  await configure(request, { inventoryError: true });
  await page.goto("/leads");
  await expect(page.locator("main").getByRole("alert")).toContainText(
    "No se pudo cargar el inventario. Intenta nuevamente.",
  );
  await expect(
    page.getByRole("button", { name: "Continuar al Pago Seguro" }),
  ).toBeDisabled();
  await configure(request, { inventoryError: false });
  await page.getByRole("button", { name: "Intenta nuevamente" }).click();
  await expect(
    page.getByRole("radio", { name: /^Leads Recientes/ }),
  ).toBeChecked();
});

test("one checkout request despite repeated submission; backend receives the chosen order", async ({
  page,
  request,
}) => {
  await configure(request, { checkoutDelay: 1000 });
  await page.route("https://checkout.stripe.com/**", (route) =>
    route.fulfill({
      contentType: "text/html",
      body: "<h1>Isolated test checkout destination</h1>",
    }),
  );
  await chooseLeads(page);
  await page.getByRole("button", { name: "Continuar al Pago Seguro" }).click();
  await expect(
    page.getByRole("button", { name: /Abriendo el pago de prueba/ }),
  ).toBeDisabled();
  await page
    .locator("form.marketplace-grid")
    .evaluate((form) =>
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      ),
    );
  await expect(page).toHaveURL(
    "https://checkout.stripe.com/c/pay/cs_test_fixture",
  );
  const result = await (await request.get(`${fixture}/state`)).json();
  expect(result.checkoutCount).toBe(1);
  expect(result.orders).toEqual([checkout]);
});

test("checkout initialization errors preserve selection and allow retry", async ({
  page,
  request,
}) => {
  await configure(request, { checkoutError: true });
  await chooseLeads(page);
  await page.getByRole("button", { name: "Continuar al Pago Seguro" }).click();
  await expect(page.locator("main").getByRole("alert")).toContainText(
    "No se pudo iniciar el proceso de pago. Intenta nuevamente.",
  );
  await expect(page.getByRole("spinbutton")).toHaveValue("2");
  await expect(
    page.getByRole("button", { name: "Continuar al Pago Seguro" }),
  ).toBeEnabled();
});

test("server blocks live checkout, unauthenticated operations, CSRF, and arbitrary proxy paths", async ({
  request,
}) => {
  expect((await request.get("/api/operations/dashboard")).status()).toBe(401);
  expect(
    (
      await request.post("/api/operations/sync", {
        headers: { Origin: origin },
      })
    ).status(),
  ).toBe(401);
  expect((await request.get("/api/marketplace/admin/leads")).status()).toBe(
    404,
  );
  expect(
    (
      await request.post("/api/marketplace/checkout", {
        data: checkout,
        headers: { Origin: "https://untrusted.example" },
      })
    ).status(),
  ).toBe(403);
  await configure(request, { mode: "live" });
  const response = await request.post("/api/marketplace/checkout", {
    data: checkout,
    headers: { Origin: origin },
  });
  expect(response.status()).toBe(409);
  expect(
    (await (await request.get(`${fixture}/state`)).json()).checkoutCount,
  ).toBe(0);
});

test("admin sign-in, private session, sync refresh, failure feedback, and sign-out", async ({
  page,
  context,
  request,
}) => {
  await signIn(page);
  const cookie = (await context.cookies()).find(
    (item) => item.name === "borinquen_operations",
  );
  expect(cookie?.httpOnly).toBe(true);
  expect(cookie?.sameSite).toBe("Strict");
  await expect(
    page.locator(".stat-card").filter({ hasText: "Leads Activos" }),
  ).toContainText("20");
  await page.getByRole("button", { name: "Sincronizar Ahora" }).click();
  await expect(
    page.getByRole("status").filter({ hasText: "Sincronización completada" }),
  ).toBeVisible();
  await expect(
    page.locator(".stat-card").filter({ hasText: "Leads Activos" }),
  ).toContainText("21");
  await expect(page.locator(".inventory-fresh")).toContainText("7 disponibles");
  await configure(request, { syncError: true });
  await page.getByRole("button", { name: "Sincronizar Ahora" }).click();
  await expect(page.locator("main").getByRole("alert")).toContainText(
    "No se pudo sincronizar la hoja de Google Sheets. Revisa la hoja e intenta nuevamente.",
  );
  await expect(
    page.getByRole("button", { name: "Sincronizar Ahora" }),
  ).toBeEnabled();
  const report = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(
    report.violations.map((v) => ({
      id: v.id,
      nodes: v.nodes.map((n) => ({
        target: n.target,
        summary: n.failureSummary,
      })),
    })),
  ).toEqual([]);
  await page.getByRole("button", { name: "Cerrar sesión" }).click();
  await expect(page.getByLabel("Contraseña")).toBeVisible();
  expect((await page.request.get("/api/operations/dashboard")).status()).toBe(
    401,
  );
});

test("invalid and tampered sessions cannot read the dashboard", async ({
  request,
  context,
}) => {
  const wrong = await request.post("/api/operations/session", {
    data: { passcode: "wrong-passcode" },
    headers: { Origin: origin },
  });
  expect(wrong.status()).toBe(401);
  await context.addCookies([
    { name: "borinquen_operations", value: "forged.signature", url: origin },
  ]);
  expect(
    (await context.request.get("/api/operations/dashboard")).status(),
  ).toBe(401);
});

test("success redirect waits for backend fulfillment; failed allocation stays visibly failed", async ({
  page,
  request,
}) => {
  await page.goto("/checkout/success?order_id=ORD-TEST0002");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Estamos confirmando tu orden.",
  );
  await configure(request, { orderStatus: "FULFILLED" });
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Tu orden está completada.",
    { timeout: 10_000 },
  );
  await expect(
    page.getByText(
      "Enviamos el correo con tus leads. Revisa tu bandeja de entrada.",
    ),
  ).toBeVisible();
  await configure(request, { orderStatus: "FULFILLMENT_FAILED" });
  await page.reload();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Tu orden requiere atención.",
  );
});

async function editRecentPrice(page: Page, value: string) {
  await page
    .getByRole("button", { name: "Editar precio de 8–30 días", exact: true })
    .click();
  await page
    .getByRole("textbox", { name: "Precio para 8–30 días", exact: true })
    .fill(value);
  await page.getByRole("button", { name: "Guardar", exact: true }).click();
}

test("editable pricing validates decimals, refreshes the marketplace, and preserves the order snapshot", async ({
  page,
  request,
}) => {
  await signIn(page);
  await page
    .getByRole("button", { name: "Editar precio de 8–30 días", exact: true })
    .click();
  const input = page.getByRole("textbox", {
    name: "Precio para 8–30 días",
    exact: true,
  });
  for (const value of ["0", "-1", "22.501", "abc", "1e2", ""]) {
    await input.fill(value);
    await page.getByRole("button", { name: "Guardar", exact: true }).click();
    await expect(page.locator("#price-feedback")).toContainText(
      "Ingresa un precio mayor de cero con un máximo de dos decimales.",
    );
    expect(
      (await (await request.get(`${fixture}/state`)).json()).prices[1],
    ).toBe(2100);
  }
  await page.getByRole("button", { name: "Cancelar", exact: true }).click();
  await editRecentPrice(page, "22.50");
  await expect(page.locator("#price-feedback")).toContainText(
    "se actualizó correctamente a $22.50",
  );
  await expect(page.locator(".inventory-recent")).toContainText("$22.50");
  await page.route("https://checkout.stripe.com/**", (route) =>
    route.fulfill({
      contentType: "text/html",
      body: "<h1>Pago de prueba aislado</h1>",
    }),
  );
  await chooseLeads(page);
  await expect(page.locator(".summary-total")).toContainText("$45.00");
  await expect(page.locator(".tier-selected")).toContainText("$22.50");
  await page.getByRole("button", { name: "Continuar al Pago Seguro" }).click();
  await expect(page).toHaveURL(
    "https://checkout.stripe.com/c/pay/cs_test_fixture",
  );
  const state = await (await request.get(`${fixture}/state`)).json();
  expect(state.orders[0].price_per_lead_cents).toBe(2250);
  expect(state.orders[0].quantity).toBe(2);
  await configure(request, { orderStatus: "FULFILLED" });
  await page.goto("/checkout/success?order_id=ORD-TEST0002");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Tu orden está completada.",
  );
  await page.goto("/admin");
  await editRecentPrice(page, "24.00");
  await expect(page.locator("#price-feedback")).toContainText(
    "se actualizó correctamente a $24.00",
  );
  await page.goto("/checkout/success?order_id=ORD-TEST0002");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Tu orden está completada.",
  );
  await expect(page.locator(".order-result-details")).toContainText("$22.50");
  await expect(page.locator(".order-result-details")).toContainText("$45.00");
});

test("pricing failures remain Spanish and the editor is accessible on mobile", async ({
  page,
  request,
}) => {
  await signIn(page);
  await configure(request, { pricingError: true });
  await editRecentPrice(page, "22.50");
  await expect(page.locator("#price-feedback")).toContainText(
    "No se pudo actualizar el precio. Intenta nuevamente.",
  );
  await expect(
    page.getByRole("textbox", { name: "Precio para 8–30 días" }),
  ).toHaveValue("22.50");
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  const report = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(
    report.violations.map((v) => ({
      id: v.id,
      nodes: v.nodes.map((n) => ({
        target: n.target,
        summary: n.failureSummary,
      })),
    })),
  ).toEqual([]);
  await configure(request, { pricingError: false });
  await page.getByRole("button", { name: "Guardar", exact: true }).click();
  await expect(page.locator("#price-feedback")).toContainText(
    "se actualizó correctamente a $22.50",
  );
});

test("pricing proxy requires authentication, origin and a price-only integer payload", async ({
  page,
  request,
}) => {
  const path = "/api/operations/pricing-rules/2";
  expect(
    (
      await request.patch(path, {
        data: { price_cents: 2250 },
        headers: { Origin: origin },
      })
    ).status(),
  ).toBe(401);
  await signIn(page);
  expect(
    (
      await page.request.patch(path, {
        data: { price_cents: 2250 },
        headers: { Origin: "https://untrusted.example" },
      })
    ).status(),
  ).toBe(403);
  for (const data of [
    { price_cents: 22.501 },
    { price_cents: -1 },
    { price_cents: 0 },
    { price_cents: "2250" },
    { price_cents: 2250, min_age_days: 10 },
    { exclusion_days: 3 },
  ]) {
    expect(
      (
        await page.request.patch(path, { data, headers: { Origin: origin } })
      ).status(),
    ).toBe(422);
  }
  expect((await (await request.get(`${fixture}/state`)).json()).prices[1]).toBe(
    2100,
  );
});
