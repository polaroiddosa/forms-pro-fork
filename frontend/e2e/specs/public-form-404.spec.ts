import { test, expect } from "../fixtures/test-data.fixture";

// Track F5: /f/<unknown> is a real HTTP 404, a published form is 200.
test.describe("Public form route status", () => {
  test("unknown form name returns 404 with a friendly page", async ({ page }) => {
    const response = await page.goto("/f/no-such-form-e2e");
    expect(response?.status()).toBe(404);
    await expect(page.getByRole("heading", { name: /not available/i })).toBeVisible();
  });

  test("published form returns 200", async ({ page, createPublishedForm }) => {
    const { route } = await createPublishedForm();
    const response = await page.goto(`/f/${route}`);
    expect(response?.status()).toBe(200);
  });

  test("unpublished form returns 404", async ({ page, createForm, apiContext }) => {
    const formId = await createForm();
    const res = await apiContext.get(`/api/resource/Form/${formId}`);
    const route = (await res.json()).data.route as string;
    const response = await page.goto(`/f/${route}`);
    expect(response?.status()).toBe(404);
  });
});
