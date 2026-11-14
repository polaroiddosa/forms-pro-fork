import type { Page } from "@playwright/test";

export class DashboardPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto("/form-builder");
  }

  // Form title headings inside FormPreviewCard
  formTitles() {
    return this.page.getByRole("heading", { level: 3 });
  }
}
