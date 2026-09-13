import { expect, test } from "@playwright/test";

async function fixture(page) {
  await page.clock.setFixedTime(new Date("2026-09-13T12:00:00Z"));
  await page.route("https://static.cloudflareinsights.com/**", (r) =>
    r.abort(),
  );
  const universities = [
    {
      id: "test-school",
      school: "Test University",
      schoolZh: "测试大学",
      qsRank: 1,
      qsPosition: 1,
      rankDisplay: "1",
      country: "Singapore",
      region: "Asia",
    },
  ];
  const records = {
    dictionaries: {
      scopes: Array.from({ length: 61 }, (_, i) => [
        `programme-${i}`,
        "programme",
        `Programme ${i}`,
      ]),
      intakes: [["Fall 2027", { term: "fall", year: 2027 }]],
      rounds: ["Main"],
      categorySets: [["international"]],
      urls: ["https://example.edu/apply", "https://example.edu/source"],
      statuses: ["official", "predicted"],
      trustStatuses: ["current"],
    },
    rows: Array.from({ length: 61 }, (_, i) => [
      `event-${i}`,
      0,
      i,
      0,
      0,
      0,
      "2026-09-01",
      "2026-09-30",
      0,
      1,
      "2026-09-12",
      "",
      i === 60 ? 1 : 0,
      -1,
      -1,
      0,
      -1,
      -1,
      0,
    ]),
  };
  await page.route("**/data/frontend-index.json", (r) =>
    r.fulfill({
      json: {
        universities,
        records,
        meta: { updatedAt: "2026-09-13T12:00:00Z" },
        applicantCategoryLabels: {
          international: { en: "International students", zh: "国际学生" },
        },
      },
    }),
  );
  await page.route("**/data/frontend-closed.json", (r) =>
    r.fulfill({ json: { records: { rows: [] } } }),
  );
  await page.route("**/data/university/test-school.json", (r) =>
    r.fulfill({ json: { records: [] } }),
  );
}

test("calendar reveals every event for a day and preserves filters in detail links", async ({
  page,
}) => {
  await fixture(page);
  await page.goto(
    "/calendar.html?region=Asia&applicant=international&deadline=30&month=2026-09",
  );
  await expect(page.locator("#calendar-result-count")).toHaveText("120 events");
  await page
    .locator(".calendar-cell")
    .filter({
      has: page.getByRole("button", { name: "30 Sept 2026", exact: true }),
    })
    .locator(".calendar-more")
    .click();
  await expect(page.locator("#calendar-result-count")).toHaveText("60 events");
  await expect(page.locator("#calendar-list .calendar-list-item")).toHaveCount(
    50,
  );
  await page.locator("#calendar-load-more").click();
  await expect(page.locator("#calendar-list .calendar-list-item")).toHaveCount(
    60,
  );
  await expect(page.locator("#calendar-load-more")).toBeHidden();
  const link = page.locator("#calendar-list .calendar-event").first();
  await expect(link).toHaveAttribute("href", /window=event-/);
  await expect(link).toHaveAttribute("href", /applicant=international/);
  await expect(page.locator(".calendar-back-link").first()).toHaveAttribute(
    "href",
    /deadline=30/,
  );
  await link.click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.locator("#applicant-filter")).toHaveValue("international");
});

test("mobile calendar starts with an agenda and has a usable month grid", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await fixture(page);
  await page.goto("/calendar.html?month=2026-09");
  await expect(page.locator("#calendar-agenda-view")).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await expect(page.locator("#calendar-month-grid")).toBeHidden();
  await page.locator("#calendar-month-view").click();
  await expect(page.locator("#calendar-month-grid")).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
  await page.getByRole("button", { name: "30 Sept 2026", exact: true }).click();
  await expect(page.locator("#calendar-list-title")).toHaveText("30 Sept 2026");
  await page.locator("#calendar-clear-day").click();
  await expect(page.locator("#calendar-result-count")).toHaveText("120 events");
});
