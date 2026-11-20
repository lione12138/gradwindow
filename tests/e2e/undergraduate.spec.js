import { expect, test } from "@playwright/test";

test("mobile visitors can switch to the international undergraduate tracker", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.clock.setFixedTime(new Date("2026-11-20T12:00:00Z"));
  await page.goto("/");
  await page.getByRole("link", { name: "Undergraduate", exact: true }).click();
  await expect(page).toHaveURL(/\/undergraduate\.html$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Undergraduate application tracker",
  );
  const cards = page.locator(".undergraduate-window");
  await expect(cards.first()).toContainText("Imperial College London");
  await expect(cards.first()).toContainText(
    "International applicants eligible",
  );
  await expect(cards.first().locator("time").last()).toHaveAttribute(
    "datetime",
    "2027-01-13",
  );
  await page.locator("#undergraduate-status").selectOption("open");
  await expect(
    page.getByText("Computer Science BA", { exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Switch language" }).click();
  await page.locator("#undergraduate-search").fill("伦敦大学学院");
  await expect(cards).toHaveCount(2);
  await expect(cards.first()).toContainText("国际生可申请");
  await expect(
    cards.first().getByRole("link", { name: "官方日期 ↗" }),
  ).toHaveAttribute("href", /www\.ucl\.ac\.uk/);
  await expect(
    page.getByRole("link", { name: "硕士", exact: true }),
  ).toBeVisible();
});
