import { expect, test } from "@playwright/test";

test("rag page loads search and ask controls", async ({ page }) => {
  await page.goto("/rag");
  await expect(page.getByRole("heading", { name: "RAG / AI" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Search" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Ask" })).toBeVisible();
});
