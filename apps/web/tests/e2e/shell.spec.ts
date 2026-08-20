import { expect, test } from "@playwright/test";

test("renders the aviation assistant shell and evidence inspector", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Airbus EASA AD Assistant" })).toBeVisible();
  await expect(page.getByText("Evidence inspector")).toBeVisible();
  await expect(page.getByRole("heading", { name: /Ask with precision/i })).toBeVisible();
  await expect(page.getByLabel("Evidence inspector")).toBeVisible();
  await expect(page.getByRole("separator", { name: "Resize evidence inspector" })).toBeVisible();
  await expect(page.getByLabel("Ask the Airbus EASA AD corpus")).toBeVisible();
  await expect(page.getByText(/controlling EASA AD/i)).toBeVisible();
});
