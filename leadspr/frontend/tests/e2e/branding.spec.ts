import { expect, test } from "@playwright/test";

test("FSG identity, verified contacts, real photos, and mobile contact navigation", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page).toHaveTitle(
    "FSG Seguros — Asesoría en seguros en Puerto Rico",
  );
  await expect(page.locator("html")).toHaveAttribute("lang", "es-PR");
  await expect(page.locator('meta[property="og:site_name"]')).toHaveAttribute(
    "content",
    "FSG Seguros",
  );
  await expect(
    page.locator("header").getByRole("link", { name: "FSG Seguros — Inicio" }),
  ).toBeVisible();
  for (const service of [
    "8 Seguros en 1",
    "Seguro de Cáncer",
    "Gastos Finales",
    "Retiro y Ahorro",
  ]) {
    await expect(
      page.getByRole("heading", { name: service, exact: true }),
    ).toBeVisible();
  }
  const contact = page.locator("#contacto");
  await expect(contact.getByRole("link", { name: /Llámanos/ })).toHaveAttribute(
    "href",
    "tel:+17876586122",
  );
  await expect(
    contact.getByRole("link", { name: /Correo electrónico/ }),
  ).toHaveAttribute("href", "mailto:0ffice@fsgseguros.com");
  await expect(contact.getByRole("link", { name: /WhatsApp/ })).toHaveAttribute(
    "href",
    "https://wa.me/17872334871",
  );
  await expect(
    page.getByRole("link", { name: "Facebook", exact: true }),
  ).toHaveAttribute("href", "https://facebook.com/segurosfsg");
  await expect(
    page.getByRole("link", { name: "Instagram", exact: true }),
  ).toHaveAttribute("href", "https://instagram.com/fsg_seguros");
  for (const width of [1440, 768, 320]) {
    await page.setViewportSize({ width, height: 900 });
    const photos = page.locator("main img");
    await expect(photos).toHaveCount(2);
    for (const photo of await photos.all()) {
      await photo.scrollIntoViewIfNeeded();
      await expect
        .poll(() =>
          photo.evaluate(
            (img: HTMLImageElement) => img.complete && img.naturalWidth > 0,
          ),
        )
        .toBe(true);
      const ratios = await photo.evaluate((img: HTMLImageElement) => ({
        actual: img.width / img.height,
        original: img.naturalWidth / img.naturalHeight,
      }));
      expect(Math.abs(ratios.actual - ratios.original)).toBeLessThan(0.02);
    }
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  }
  await page
    .getByRole("link", { name: "Solicita orientación gratis", exact: true })
    .click();
  await expect(page).toHaveURL(/#contacto$/);
  await expect(
    page.getByRole("heading", { name: "Hablemos de tu próximo paso." }),
  ).toBeInViewport();
  for (const route of [
    "/",
    "/leads",
    "/admin",
    "/checkout/cancel",
    "/checkout/success",
    "/pagina-inexistente",
  ]) {
    await page.goto(route);
    await expect(page.locator("body")).not.toContainText(
      /Borinquen|Cobertura para Hoy|Protección para Mañana/,
    );
    await expect(page).toHaveTitle(/FSG Seguros/);
  }
});
