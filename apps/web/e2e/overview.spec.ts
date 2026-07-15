import { expect, test } from "@playwright/test";

test("overview page loads and shows dashboard heading", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  await expect(page.getByText("Cross-scan FinOps and posture signals")).toBeVisible();
});
