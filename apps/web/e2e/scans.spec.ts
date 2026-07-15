import { expect, test } from "@playwright/test";

test("scans page loads and lists scan table", async ({ page }) => {
  await page.goto("/scans");
  await expect(page.getByRole("heading", { name: "Scans" })).toBeVisible();
  await expect(page.getByRole("button", { name: "New scan" })).toBeVisible();
});
