import { expect, test } from "@playwright/test";

async function openTracker(page) {
  await page.route("https://static.cloudflareinsights.com/**", (route) =>
    route.abort(),
  );
  await page.goto("/");
  await expect(page.locator("#results-school-count")).toHaveAttribute(
    "data-count",
    /\d+/,
  );
}

async function firstWindowFavorite(page) {
  const favorite = page.locator(".favorite-button[data-favorite-key]").first();
  await expect(favorite).toBeVisible();
  return favorite;
}

test("homepage loads the tracker without runtime errors", async ({ page }) => {
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));

  await openTracker(page);

  await expect(page).toHaveTitle(/Global Top-200 Master's Applications/);
  await expect(
    page.locator("#application-groups .application-table").first(),
  ).toBeVisible();
  await expect(page.locator("#monitoring-health")).toContainText(
    "adapters healthy",
  );
  expect(pageErrors).toEqual([]);
});

test("wide desktop places the filters beside the application results", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await openTracker(page);

  const sidebar = page.locator(".tracker-sidebar");
  const results = page.locator(".tracker-results");
  const sidebarBox = await sidebar.boundingBox();
  const resultsBox = await results.boundingBox();

  expect(sidebarBox).not.toBeNull();
  expect(resultsBox).not.toBeNull();
  expect(sidebarBox.width).toBeGreaterThanOrEqual(260);
  expect(sidebarBox.width).toBeLessThanOrEqual(296);
  expect(sidebarBox.x + sidebarBox.width).toBeLessThan(resultsBox.x);
  await expect(sidebar).toHaveCSS("position", "sticky");

  const statusButtons = page.locator(".primary-status-tabs .status-tab");
  const firstStatusBox = await statusButtons.nth(0).boundingBox();
  const secondStatusBox = await statusButtons.nth(1).boundingBox();
  expect(firstStatusBox).not.toBeNull();
  expect(secondStatusBox).not.toBeNull();
  expect(secondStatusBox.y).toBeGreaterThan(firstStatusBox.y);
  expect(secondStatusBox.x).toBe(firstStatusBox.x);
});

test("hero search finds NUS across application statuses", async ({ page }) => {
  await openTracker(page);

  await page.locator("#hero-search-input").fill("NUS");
  await page.getByRole("button", { name: "Search", exact: true }).click();

  await expect(page).toHaveURL(/\?q=NUS/);
  await expect(page.locator("#application-groups")).toContainText(
    "National University of Singapore",
  );
});

test("Open now restores the primary status view", async ({ page }) => {
  await openTracker(page);
  const upcoming = page.locator('.status-tab[data-status="upcoming"]');
  const open = page.locator('.status-tab[data-status="open"]');

  await upcoming.click();
  await expect(upcoming).toHaveAttribute("aria-selected", "true");
  await expect(page).toHaveURL(/status=upcoming/);

  await open.click();
  await expect(open).toHaveAttribute("aria-selected", "true");
  await expect(page).not.toHaveURL(/status=/);
  await expect(page.locator("#results-window-count")).not.toHaveText(
    "0 windows",
  );
});

test("advanced rank filtering updates results and the shareable URL", async ({
  page,
}) => {
  await openTracker(page);

  await page.locator("#mobile-filter-toggle").click();
  await expect(page.locator("#advanced-filter-panel")).toBeVisible();
  await page.locator("#rank-range-filter").selectOption("30");

  await expect(page).toHaveURL(/rank=30/);
  await expect(page.locator("#rank-range-filter")).toHaveValue("30");
  const count = Number(
    await page.locator("#results-school-count").getAttribute("data-count"),
  );
  expect(count).toBeGreaterThan(0);
  expect(count).toBeLessThanOrEqual(30);
});

test("advanced date filters are progressive and shareable", async ({
  page,
}) => {
  await openTracker(page);

  await expect(page.locator("#advanced-filter-panel")).not.toBeVisible();
  await page.locator("#mobile-filter-toggle").click();
  await expect(page.locator("#applicant-filter")).toBeVisible();
  await expect(page.locator("#deadline-range-filter")).toBeVisible();
  await expect(page.locator("#date-type-filter")).toBeVisible();

  await page.locator("#deadline-range-filter").selectOption("90");
  await expect(page).toHaveURL(/deadline=90/);
  await page.locator("#date-type-filter").selectOption("official");
  await expect(page).toHaveURL(/dates=official/);
});

test("saving a deadline updates the saved workflow", async ({ page }) => {
  await openTracker(page);
  const favorite = await firstWindowFavorite(page);

  await favorite.click();

  await expect(page.locator("#favorite-count")).toHaveText("1");
  await expect(page.locator("#favorites-sync-notice")).toBeVisible();
  const stored = await page.evaluate(() =>
    JSON.parse(window.localStorage.getItem("gradwindow:favorites") || "[]"),
  );
  expect(stored).toHaveLength(1);

  await page.locator("#saved-status-tab").click();
  await expect(page.locator("#saved-status-tab")).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await expect(page).toHaveURL(/saved=1/);
});

test("saved deadlines survive a page reload", async ({ page }) => {
  await openTracker(page);
  const favorite = await firstWindowFavorite(page);
  const key = await favorite.getAttribute("data-favorite-key");
  await favorite.click();

  await page.reload();
  await expect(page.locator("#results-school-count")).toHaveAttribute(
    "data-count",
    /\d+/,
  );

  const restored = page.locator(`.favorite-button[data-favorite-key="${key}"]`);
  await expect(restored).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator("#favorite-count")).toHaveText("1");
});

test("a deadline row opens and closes the detail drawer", async ({ page }) => {
  await openTracker(page);
  const row = page
    .locator(".window-card-row:not(.university-group-parent)")
    .first();
  await expect(row).toBeVisible();

  await row.locator("td").nth(3).click();

  const panel = page.locator("#window-detail-panel");
  await expect(panel).toBeVisible();
  await expect(panel.locator("#window-detail-body h2")).not.toBeEmpty();
  await page.keyboard.press("Escape");
  await expect(panel).toBeHidden();
});

test.describe("mobile filters", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("keeps filters above the results on narrow screens", async ({
    page,
  }) => {
    await openTracker(page);
    const sidebarBox = await page.locator(".tracker-sidebar").boundingBox();
    const resultsBox = await page.locator(".tracker-results").boundingBox();

    expect(sidebarBox).not.toBeNull();
    expect(resultsBox).not.toBeNull();
    expect(sidebarBox.y + sidebarBox.height).toBeLessThanOrEqual(resultsBox.y);
  });

  test("filter drawer reports the result count before applying", async ({
    page,
  }) => {
    await openTracker(page);
    const toggle = page.locator("#mobile-filter-toggle");

    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-expanded", "true");
    await expect(page.locator("#advanced-filter-panel")).toBeVisible();

    await page.locator("#rank-range-filter").selectOption("30");
    const apply = page.locator("#mobile-filter-apply");
    await expect(apply).toBeVisible();
    await expect(apply).toHaveText(/Show \d+ universities/);
    await apply.click();
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
  });

  test("bottom navigation keeps the four primary destinations", async ({
    page,
  }) => {
    await openTracker(page);
    await expect(
      page.locator(".mobile-bottom-nav [data-mobile-nav]"),
    ).toHaveCount(4);
    await expect(
      page.locator('.mobile-bottom-nav [data-mobile-nav="calendar"]'),
    ).toHaveAttribute("href", "./calendar.html");

    await page
      .locator('.mobile-bottom-nav [data-mobile-nav="profile"]')
      .click();
    await expect(page.locator(".mobile-account-menu")).toBeVisible();
    await expect(page.locator("#mobile-theme-toggle")).toBeVisible();
  });
});
