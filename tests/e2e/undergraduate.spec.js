import { expect, test } from "@playwright/test";

test("mobile visitors can switch to the undergraduate board and expand a school", async ({
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
  const rows = page.locator(".undergraduate-table tbody tr");
  await expect(rows).toHaveCount(5);
  await expect(rows.first()).toContainText("Imperial College London");
  await expect(rows.first()).toContainText("International applicants eligible");
  await expect(rows.first().locator("time").last()).toHaveAttribute(
    "datetime",
    "2027-01-13",
  );
  await page.getByRole("button", { name: /Open now/ }).click();
  await expect(
    page.getByText("Computer Science BA", { exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Switch language" }).click();
  await page.locator("#undergraduate-search").fill("伦敦大学学院");
  await expect(rows).toHaveCount(1);
  await expect(rows.first()).toContainText("伦敦大学学院");
  const toggle = rows.first().locator(".university-group-toggle");
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
  await toggle.press("Enter");
  await expect(toggle).toHaveAttribute("aria-expanded", "true");
  await expect(toggle).toBeFocused();
  const projects = page.locator(".university-group-child");
  await expect(projects).toHaveCount(2);
  await expect(projects.first().getByText("国际生可申请")).toBeVisible();
  await expect(
    projects.first().locator('time[datetime="2026-09-01"]'),
  ).toBeVisible();
  await expect(
    projects.first().getByRole("link", { name: "官方日期 ↗" }),
  ).toHaveAttribute("href", /www\.ucl\.ac\.uk/);
  await expect(
    page.getByRole("link", { name: "硕士", exact: true }),
  ).toBeVisible();
});

test("wide undergraduate board shares the tracker sidebar and ranked table", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1600, height: 900 });
  await page.goto("/undergraduate.html");
  const table = page.locator(".undergraduate-table");
  await expect(table).toBeVisible();
  const sidebar = await page.locator(".tracker-sidebar").boundingBox();
  const results = await page.locator(".tracker-results").boundingBox();
  expect(sidebar.x + sidebar.width).toBeLessThan(results.x);
  await expect(
    table.getByRole("columnheader", { name: /QS rank/ }),
  ).toHaveAttribute("aria-sort", "ascending");
  await expect(table.locator("tbody tr").first()).toContainText(
    "Imperial College London",
  );
  await page.locator("#undergraduate-region").selectOption("Europe");
  await expect(table.locator("tbody tr")).toHaveCount(3);
  await page
    .getByRole("button", { name: "Expand schools on this page" })
    .click();
  await expect(table.locator(".university-group-child")).toHaveCount(2);
  await page.getByRole("button", { name: "Collapse all" }).click();
  await expect(table.locator(".university-group-child")).toHaveCount(0);
});
