import { expect, test } from "@playwright/test";

test("renders the aviation assistant shell and evidence inspector", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Airbus EASA AD Assistant" })).toBeVisible();
  await expect(page.getByText("Evidence inspector")).toBeVisible();
  await expect(page.getByText(/controlling EASA AD/i)).toBeVisible();
});
