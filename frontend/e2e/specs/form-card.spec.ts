import { test, expect } from "../fixtures/test-data.fixture";
import { DashboardPage } from "../helpers/dashboard";

// Track F5 (not run in CI here: needs a bench with a browser; see CHANGES-F5.md).
test.describe("My forms card", () => {
  test("shows the answers count and a Copy link button for the public /f/ link", async ({
    page,
    context,
    createPublishedForm,
  }) => {
    const { route } = await createPublishedForm();
    await context.grantPermissions(["clipboard-read", "clipboard-write"]);

    const dashboard = new DashboardPage(page);
    await dashboard.goto();

    const card = page.locator("[data-form-card-answers]").first();
    await expect(card).toHaveText(/No answers yet|\d+ answers?/);

    const copyButtons = page.locator("[data-form-card-copy-link]");
    await expect(copyButtons.first()).toBeVisible();
    await copyButtons.first().click();
    // A click on the button must not open the form (the card itself is a link).
    await expect(page).toHaveURL(/\/form-builder\/?$/);

    const copied = await page.evaluate(() => navigator.clipboard.readText());
    expect(copied).toMatch(/\/f\/[^/]+/);
    expect(route).toBeTruthy();
  });
});
