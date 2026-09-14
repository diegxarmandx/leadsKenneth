import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
const fixture = "http://127.0.0.1:4319/__test";

async function openForm(page: Page) {
  await page.goto("/admin");
  await page.getByLabel("Contraseña").fill("automated-test-passcode");
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await page.getByRole("button", { name: "Añadir Lead", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Nuevo Lead", exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel("Municipio", { exact: true })).toBeEnabled();
}
async function fillLead(page: Page) {
  await page.getByLabel("Nombre", { exact: true }).fill("Prueba Admin");
  await page.getByLabel("Apellido", { exact: false }).fill("Demo");
  await page.getByLabel("Teléfono", { exact: true }).fill("+1 (787) 555-0100");
  await page
    .getByLabel("Correo Electrónico", { exact: false })
    .fill("lead@example.com");
  await page.getByLabel("Municipio", { exact: true }).selectOption("Salinas");
}
test.beforeEach(async ({ request }) => {
  await request.post(`${fixture}/reset`);
});

test("admin validates, adds one lead, closes the form and refreshes inventory", async ({
  page,
  request,
}) => {
  await openForm(page);
  await expect(page.getByLabel("Fecha del Lead")).toHaveValue("2026-09-13");
  await page.getByRole("button", { name: "Guardar Lead", exact: true }).click();
  await expect(
    page.getByText("Ingresa el nombre (máximo 100 caracteres).", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByText("Ingresa un teléfono válido de 7 a 15 dígitos.", {
      exact: true,
    }),
  ).toBeVisible();
  expect(
    (await (await request.get(`${fixture}/state`)).json()).leadRequests,
  ).toBe(0);
  await fillLead(page);
  await page
    .getByLabel("Correo Electrónico", { exact: false })
    .fill("invalid-email");
  await page.getByRole("button", { name: "Guardar Lead", exact: true }).click();
  await expect(
    page.getByText("Ingresa un correo electrónico válido.", { exact: true }),
  ).toBeVisible();
  await page
    .getByLabel("Correo Electrónico", { exact: false })
    .fill("lead@example.com");
  await request.post(`${fixture}/state`, { data: { leadDelay: 500 } });
  await page.getByRole("button", { name: "Guardar Lead", exact: true }).click();
  await expect(
    page.getByRole("button", { name: /Añadiendo lead/ }),
  ).toBeDisabled();
  await page
    .locator("#new-lead-form")
    .evaluate((form) =>
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      ),
    );
  await expect(
    page.getByText(/Lead añadido y sincronizado correctamente/),
  ).toBeVisible();
  await expect(page.locator("#new-lead-form")).toHaveCount(0);
  await expect(
    page
      .locator(".stat-card")
      .filter({ hasText: "Leads Activos" })
      .locator(".stat-value"),
  ).toHaveText("21");
  await expect(page.locator(".inventory-fresh .availability")).toContainText(
    "7 disponibles",
  );
  const state = await (await request.get(`${fixture}/state`)).json();
  expect(state.leadRequests).toBe(1);
  expect(state.leadRows).toHaveLength(1);
  expect(state.leadRows[0].phone).toBe("+1 (787) 555-0100");
  await page.getByRole("button", { name: "Añadir Lead", exact: true }).click();
  await expect(page.getByLabel("Nombre", { exact: true })).toHaveValue("");
  await page.goto("/leads");
  await expect(
    page.getByRole("radio", { name: /Leads Nuevos.*7 disponibles/ }),
  ).toBeVisible();
});

test("partial sync success closes the form and directs admin to sync without reappending", async ({
  page,
  request,
}) => {
  await request.post(`${fixture}/state`, { data: { leadMode: "partial" } });
  await openForm(page);
  await fillLead(page);
  await page.getByLabel("Fecha del Lead").fill("2026-09-01");
  await page.getByRole("button", { name: "Guardar Lead", exact: true }).click();
  await expect(
    page.getByText(
      /El lead fue añadido a Google Sheets, pero no se pudo completar/,
    ),
  ).toBeVisible();
  await expect(page.locator("#new-lead-form")).toHaveCount(0);
  await expect(
    page
      .locator(".stat-card")
      .filter({ hasText: "Leads Activos" })
      .locator(".stat-value"),
  ).toHaveText("20");
  await page.getByRole("button", { name: "Sincronizar Ahora" }).click();
  await expect(page.getByText(/Sincronización completada/)).toBeVisible();
  const state = await (await request.get(`${fixture}/state`)).json();
  expect(state.leadRows).toHaveLength(1);
  expect(state.leadRows[0].lead_date).toBe("2026-09-01");
  expect(state.leadRequests).toBe(1);
});

test("write failures preserve the draft and retry key; form is accessible on mobile", async ({
  page,
  request,
}) => {
  const keys: string[] = [];
  page.on("request", (req) => {
    if (req.url().endsWith("/api/operations/leads"))
      keys.push(req.headers()["idempotency-key"]);
  });
  await request.post(`${fixture}/state`, { data: { leadMode: "write_error" } });
  await openForm(page);
  await fillLead(page);
  await page.getByRole("button", { name: "Guardar Lead", exact: true }).click();
  await expect(
    page.locator(".lead-entry-panel").getByRole("alert"),
  ).toContainText("No se pudo confirmar el lead en Google Sheets");
  await expect(page.getByLabel("Nombre", { exact: true })).toHaveValue(
    "Prueba Admin",
  );
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
      nodes: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
  await request.post(`${fixture}/state`, { data: { leadMode: "success" } });
  await page.getByRole("button", { name: "Guardar Lead", exact: true }).click();
  await expect(
    page.getByText(/Lead añadido y sincronizado correctamente/),
  ).toBeVisible();
  expect(keys).toHaveLength(2);
  expect(keys[0]).toBe(keys[1]);
});

test("add-lead proxy requires admin session, same origin, and allowed fields", async ({
  page,
  request,
}) => {
  const headers = {
    Origin: "http://localhost:4318",
    "Idempotency-Key": "55f05b44-d60c-41e3-bb91-815ee9b75c61",
  };
  expect(
    (
      await request.post("/api/operations/leads", { headers, data: {} })
    ).status(),
  ).toBe(401);
  await openForm(page);
  expect(
    (
      await page.request.post("/api/operations/leads", {
        headers: { ...headers, Origin: "https://untrusted.example" },
        data: {},
      })
    ).status(),
  ).toBe(403);
  expect(
    (
      await page.request.post("/api/operations/leads", {
        headers,
        data: { external_id: "tampered" },
      })
    ).status(),
  ).toBe(422);
  expect(
    (await (await request.get(`${fixture}/state`)).json()).leadRequests,
  ).toBe(0);
});
