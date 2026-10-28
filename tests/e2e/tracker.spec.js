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

async function overrideSchoolWindows(page, schoolId, updateRow) {
  const index = await (
    await page.request.get("/data/frontend-index.json")
  ).json();
  const schoolIndex = index.universities.findIndex(
    (item) => item.id === schoolId,
  );
  expect(schoolIndex).toBeGreaterThanOrEqual(0);
  for (const file of ["frontend-index.json", "frontend-closed.json"]) {
    await page.route(`**/data/${file}`, async (route) => {
      const response = await route.fetch();
      const payload = await response.json();
      const dictionaries = payload.records.dictionaries;
      const trustIndex = (status) => {
        if (!dictionaries.trustStatuses.includes(status))
          dictionaries.trustStatuses.push(status);
        return dictionaries.trustStatuses.indexOf(status);
      };
      for (const row of payload.records.rows) {
        if (
          row[1] === schoolIndex &&
          dictionaries.statuses[row[12]] === "official"
        )
          updateRow(row, trustIndex, dictionaries);
      }
      await route.fulfill({ response, json: payload });
    });
  }
}

test("deadline-only facts remain visible alongside a school's full windows", async ({
  page,
}) => {
  const { programs } = await (
    await page.request.get("/data/programs.json")
  ).json();
  const programme = programs.find(
    (p) => p.universityId === "imperial-college-london",
  );
  await page.route("**/data/reviewed-deadlines.json", (route) =>
    route.fulfill({
      json: {
        deadlines: [
          {
            id: "fixture-deadline",
            universityId: programme.universityId,
            programmeId: programme.id,
            intake: "2027",
            round: "Fixture round",
            applicantCategories: ["all"],
            closesAt: "2026-12-01",
            opensAt: null,
            sourceUrl: programme.sourceUrl,
            verifiedAt: "2026-10-15",
            dataStatus: "deadline-only",
          },
        ],
      },
    }),
  );
  await openTracker(page);
  await page.locator('.status-tab[data-status="all"]').click();
  await expect(
    page.locator('[data-school-id="imperial-college-london"]'),
  ).not.toHaveClass(/catalogue-group-parent/);
  await page
    .locator(
      '[data-group-key="catalogue:imperial-college-london"] .university-group-toggle',
    )
    .click();
  await expect(
    page.locator('[data-deadline-only="fixture-deadline"]'),
  ).toBeVisible();
});

test("reviewed deadline-only facts do not invent openings or calendar events", async ({
  page,
}) => {
  await openTracker(page);
  const openCount = await page
    .locator('.status-tab[data-status="open"]')
    .textContent();
  await page.locator('.status-tab[data-status="all"]').click();
  await page
    .locator('[data-school-id="harvard-university"] .university-group-toggle')
    .click();
  const row = page.locator(
    '[data-deadline-only="harvard-data-science-sm-2027-deadline"]',
  );
  await expect(row).toBeVisible();
  await expect(row.locator("td").nth(4)).toContainText(
    "Exact opening date not verified",
  );
  await expect(row.locator("td").nth(5)).toContainText("1 Dec 2026");
  await expect(row).toContainText("Reviewed deadline only");
  await expect(row.locator(".calendar-menu")).toHaveCount(0);
  await expect(page.locator('.status-tab[data-status="open"]')).toHaveText(
    openCount,
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await row.scrollIntoViewIfNeeded();
  await expect(row.locator("td").nth(4)).toBeVisible();
  await expect(row.locator("td").nth(7)).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({ path: "test-results/deadline-only-mobile.png" });
  await page.locator('.status-tab[data-status="open"]').click();
  await expect(page.locator(".deadline-only-row")).toHaveCount(0);
});

test("MIT retains unavailable-source dates only in a separate review section", async ({
  page,
}) => {
  await page.clock.setFixedTime(new Date("2026-10-26T12:00:00Z"));
  await overrideSchoolWindows(
    page,
    "massachusetts-institute-of-technology-mit",
    (row, trustIndex) => {
      row[6] = "2025-09-01";
      row[7] = "2026-01-15";
      row[18] = trustIndex("source-unavailable");
    },
  );
  await openTracker(page);
  await page.locator('.status-tab[data-status="all"]').click();
  const review = page.locator(
    '[data-review-school="massachusetts-institute-of-technology-mit"]',
  );
  await expect(review).toContainText("View historical dates");
  await expect(
    page
      .locator(
        '[data-school-id="massachusetts-institute-of-technology-mit"] td',
      )
      .nth(1)
      .locator("[data-review-school]"),
  ).toHaveCount(1);
  await expect(page.locator(".review-window-heading")).toHaveCount(0);
  await page.locator("#expand-visible-groups").click();
  await expect(review.getByRole("button")).toHaveAttribute(
    "aria-expanded",
    "false",
  );
  await expect(page.locator(".review-window-heading")).toHaveCount(0);
  await page.locator("#collapse-visible-groups").click();
  await page.screenshot({ path: "test-results/history-entry-desktop.png" });
  await page.setViewportSize({ width: 390, height: 844 });
  await review.scrollIntoViewIfNeeded();
  await expect(review.getByRole("button")).toBeVisible();
  await page.screenshot({ path: "test-results/history-entry-mobile.png" });
  await page.setViewportSize({ width: 1440, height: 900 });
  await review.getByRole("button").click();
  const rows = page.locator(
    '.review-window-row[data-university-id="massachusetts-institute-of-technology-mit"]',
  );
  await expect(rows.first()).toBeVisible();
  await expect(rows.first()).toContainText("Last verified dates");
  await expect(rows.first()).toContainText("Source unavailable");
  await expect(rows.first().locator("td").nth(4)).toContainText("1 Sept 2025");
  await expect(rows.first().locator(".calendar-menu-trigger")).toHaveCount(0);
  await expect(rows.first()).not.toContainText("Open now");
  await page.setViewportSize({ width: 390, height: 844 });
  await rows.first().scrollIntoViewIfNeeded();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({ path: "test-results/mit-review-mobile.png" });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.locator("#collapse-visible-groups").click();
  await expect(rows).toHaveCount(0);
  await page.locator('.status-tab[data-status="open"]').click();
  await expect(page.locator(".review-window-row")).toHaveCount(0);
  await page.goto("/?q=MIT");
  const historyToggle = page.locator(".history-results-toggle");
  await expect(historyToggle).toHaveAttribute("aria-expanded", "false");
  await expect(page.locator("#history-results-content")).toBeHidden();
  await historyToggle.focus();
  await page.keyboard.press("Enter");
  await expect(historyToggle).toHaveAttribute("aria-expanded", "true");
  await expect(historyToggle).toBeFocused();
  await expect(review).toBeVisible();
  await expect(review).toContainText("Massachusetts Institute of Technology");
  await expect(page.locator("#history-results-content")).not.toContainText(
    "undefined",
  );
  await review.getByRole("button").click();
  await expect(rows.first()).toBeVisible();
  await expect(
    page.locator(".review-window-row .calendar-menu-trigger"),
  ).toHaveCount(0);
  await page.locator("#collapse-visible-groups").click();
  await expect(historyToggle).toHaveAttribute("aria-expanded", "false");
  await expect(page.locator("#history-results-content")).toBeHidden();
  await historyToggle.click();
  await review.getByRole("button").click();
  await rows.first().locator(".favorite-button").click();
  await page.goto("/?saved=1");
  await expect(historyToggle).toHaveAttribute("aria-expanded", "false");
  await expect(page.locator("#history-results-content")).toBeHidden();
  await historyToggle.click();
  await expect(review).toContainText("Massachusetts Institute of Technology");
  await review.getByRole("button").click();
  await expect(rows).toHaveCount(1);
  await expect(rows.first().locator(".calendar-menu-trigger")).toHaveCount(0);
  await page.setViewportSize({ width: 390, height: 844 });
  await historyToggle.click();
  await historyToggle.evaluate((button) =>
    button.scrollIntoView({ block: "center" }),
  );
  await expect(historyToggle).toBeVisible();
  await historyToggle.click({ trial: true });
  await page.screenshot({
    path: "test-results/saved-history-collapsed-mobile.png",
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("UCL exposes its programme catalogue when no verified windows are visible", async ({
  page,
}) => {
  const index = await (
    await page.request.get("/data/frontend-index.json")
  ).json();
  const uclIndex = index.universities.findIndex(
    (school) => school.id === "ucl-university-college-london",
  );
  expect(uclIndex).toBeGreaterThanOrEqual(0);
  for (const file of ["frontend-index.json", "frontend-closed.json"]) {
    await page.route(`**/data/${file}`, async (route) => {
      const response = await route.fetch();
      const payload = await response.json();
      payload.records.rows = payload.records.rows.filter(
        (row) => row[1] !== uclIndex,
      );
      await route.fulfill({ response, json: payload });
    });
  }
  await openTracker(page);
  await page.locator('.status-tab[data-status="all"]').click();
  const ucl = page.locator('[data-school-id="ucl-university-college-london"]');
  await expect(ucl).toHaveClass(/university-group-parent--collapsed/);
  await ucl.locator(".university-group-toggle").click();
  await expect(ucl).toHaveAttribute("data-group-state", "expanded");
  const children = page.locator(
    '[data-catalogue-school="ucl-university-college-london"]',
  );
  await expect(children).toHaveCount(20);
  await expect(children.first().locator("td")).toHaveCount(8);
  await expect(children.first().locator("td").nth(2)).toContainText(
    "Advanced Audiology",
  );
  await expect(children.first().locator("td").nth(4)).toHaveText("—");
  await expect(children.first().locator(".calendar-menu-trigger")).toHaveCount(
    0,
  );
  await expect(page.locator(".programme-catalogue-list")).toHaveCount(0);
  await ucl
    .locator(
      "xpath=following-sibling::tr[contains(@class,'catalogue-pagination-row')][1]",
    )
    .getByRole("button")
    .click();
  await expect(children).toHaveCount(40);
  await page.locator("#collapse-visible-groups").click();
  await expect(children).toHaveCount(0);
  await ucl.locator(".university-group-toggle").click();
  await expect(children).toHaveCount(40);
  await ucl.scrollIntoViewIfNeeded();
  await page.screenshot({ path: "test-results/ucl-unified-desktop.png" });
  await page.setViewportSize({ width: 390, height: 844 });
  await children.first().scrollIntoViewIfNeeded();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({ path: "test-results/ucl-unified-mobile.png" });
});

test("UCL reviewed 2027 windows show visa-specific dates and calendar actions", async ({
  page,
}) => {
  await page.clock.setFixedTime(new Date("2026-10-26T12:00:00Z"));
  await overrideSchoolWindows(
    page,
    "ucl-university-college-london",
    (row, trustIndex) => {
      if (row[0].includes("-2027-")) row[18] = trustIndex("current");
    },
  );
  await openTracker(page);
  await page.locator('.status-tab[data-status="all"]').click();
  const ucl = page.locator('[data-school-id="ucl-university-college-london"]');
  await expect(ucl).toContainText("School application group");
  await ucl.locator(".university-group-toggle").click();
  const rows = page.locator(".university-group-child").filter({
    has: page.getByRole("link", {
      name: "Advanced Materials Science MSc",
      exact: true,
    }),
  });
  await expect(rows).toHaveCount(2);
  for (const [category, deadline] of [
    ["Applicants requiring a UK Student visa", "25 Jun 2027"],
    ["Applicants not requiring a UK Student visa", "27 Aug 2027"],
  ]) {
    const row = rows.filter({
      has: page.getByRole("cell", { name: category, exact: true }),
    });
    await expect(row.locator("td").nth(4)).toContainText("19 Oct 2026");
    await expect(row.locator("td").nth(5)).toContainText(deadline);
    await expect(row.locator(".calendar-menu-trigger")).toBeVisible();
    await row.getByRole("button", { name: /Show .* more programmes/ }).click();
  }
  await expect(
    page.getByRole("link", { name: "Law and Finance MSc", exact: true }),
  ).toHaveCount(2);
});

test("UCL blocked current-cycle sources remain reviewable without becoming historical or actionable", async ({
  page,
}) => {
  await page.clock.setFixedTime(new Date("2026-10-26T12:00:00Z"));
  await overrideSchoolWindows(
    page,
    "ucl-university-college-london",
    (row, trustIndex) => {
      row[18] = trustIndex("source-unavailable");
    },
  );
  await page.goto("/?university=ucl-university-college-london&status=all");
  const pending = page.locator(
    '[data-review-school="ucl-university-college-london"][data-review-kind="pending"]',
  );
  const historical = page.locator(
    '[data-review-school="ucl-university-college-london"][data-review-kind="history"]',
  );
  const pendingRows = page.locator(
    '.review-window-row[data-university-id="ucl-university-college-london"][data-review-kind="pending"]',
  );
  await expect(pending).toContainText("View dates pending recheck (4)");
  await expect(historical).toContainText("View historical dates (20)");
  await expect(page.locator("#count-open")).toHaveText("0");
  await expect(page.locator("#count-exception")).toHaveText("1");
  await pending.getByRole("button").click();
  await expect(pendingRows).toHaveCount(4);
  await expect(pendingRows.first()).toContainText("Source unavailable");
  await expect(pendingRows.first().locator("td").nth(4)).toContainText(
    "19 Oct 2026",
  );
  await expect(pendingRows.first().locator("td").nth(5)).toContainText("2027");
  await expect(pendingRows.locator(".calendar-menu-trigger")).toHaveCount(0);
  await expect(historical.getByRole("button")).toHaveAttribute(
    "aria-expanded",
    "false",
  );
  await pendingRows.first().locator(".favorite-button").click();
  await expect(page.locator("#export-favorites")).toBeDisabled();
  await page.locator('.status-tab[data-status="exception"]').click();
  await expect(pending).toBeVisible();
  await pending.getByRole("button").click();
  await expect(pendingRows).toHaveCount(4);
  await expect(page.locator("#results-school-count")).toHaveAttribute(
    "data-count",
    "1",
  );
  await expect(
    page.locator(
      '.university-table [data-university-id="ucl-university-college-london"]',
    ),
  ).toHaveCount(0);
  await page.goto("/?q=Law%20and%20Finance");
  await expect(pending).toBeVisible();
  await expect(page.locator("#count-all")).toHaveText("1");
  await pending.getByRole("button").click();
  await expect(pendingRows).toHaveCount(2);
  await expect(page.locator("#results-school-count")).toHaveAttribute(
    "data-count",
    "1",
  );
  await expect(page.locator(".history-results-toggle")).toHaveCount(0);
  await page.goto("/?saved=1");
  await expect(pending).toBeVisible();
  await pending.getByRole("button").click();
  await expect(pendingRows).toHaveCount(1);
  await expect(page.locator("#export-favorites")).toBeDisabled();
  await page.setViewportSize({ width: 390, height: 844 });
  await pendingRows.first().scrollIntoViewIfNeeded();
  await expect(pendingRows.first().locator("td").nth(7)).toContainText(
    "Source unavailable",
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/ucl-blocked-pending-mobile.png",
  });
});

test("review dates use deadline semantics rather than trust status to decide history", async ({
  page,
}) => {
  await page.clock.setFixedTime(new Date("2026-10-26T12:00:00Z"));
  await overrideSchoolWindows(
    page,
    "ucl-university-college-london",
    (row, trustIndex, dictionaries) => {
      row[18] = trustIndex("stale");
      if (!row[0].includes("-2027-")) return;
      row[6] = "2026-10-01";
      row[7] = "2026-10-26";
      const semantics = row[0].includes("does-not-require") ? "on" : "before";
      if (!dictionaries.deadlineSemantics.includes(semantics))
        dictionaries.deadlineSemantics.push(semantics);
      row[17] = dictionaries.deadlineSemantics.indexOf(semantics);
    },
  );
  await page.goto("/?university=ucl-university-college-london&status=all");
  await expect(page.locator('[data-review-kind="pending"]')).toContainText(
    "View dates pending recheck (2)",
  );
  await expect(page.locator('[data-review-kind="history"]')).toContainText(
    "View historical dates (22)",
  );
  await expect(page.locator("#count-open")).toHaveText("0");
});

test("saved calendar export excludes pending review dates from mixed favorites", async ({
  page,
}) => {
  const currentId =
    "ucl-advanced-materials-science-msc-2027-application-period-requires-uk-study-visa";
  await page.clock.setFixedTime(new Date("2026-10-26T12:00:00Z"));
  await overrideSchoolWindows(
    page,
    "ucl-university-college-london",
    (row, trustIndex) => {
      row[18] = trustIndex(
        row[0] === currentId ? "current" : "source-unavailable",
      );
    },
  );
  await page.goto("/?university=ucl-university-college-london&status=all");
  await page
    .locator(`.favorite-button[data-favorite-key="window:${currentId}"]`)
    .click();
  await page.locator('[data-review-kind="pending"] button').click();
  const pendingFavorite = page
    .locator('.review-window-row[data-review-kind="pending"] .favorite-button')
    .first();
  const pendingId = (
    await pendingFavorite.getAttribute("data-favorite-key")
  ).slice(7);
  await pendingFavorite.click();
  await page.locator("#mobile-filter-toggle").click();
  await expect(page.locator("#export-favorites")).toBeEnabled();
  // Inspect the real export payload without relying on OS download permissions.
  await page.evaluate(() => {
    const createObjectURL = URL.createObjectURL.bind(URL);
    window.calendarExportPayloads = [];
    URL.createObjectURL = (blob) => {
      window.calendarExportPayloads.push(blob.text());
      return createObjectURL(blob);
    };
  });
  const downloadEvent = page.waitForEvent("download");
  await page.locator("#export-favorites").click();
  const download = await downloadEvent;
  expect(download.suggestedFilename()).toBe(
    "gradwindow-favorite-deadlines.ics",
  );
  const payloads = await page.evaluate(() =>
    Promise.all(window.calendarExportPayloads),
  );
  expect(payloads).toHaveLength(1);
  const [calendar] = payloads;
  expect(calendar).toContain(`UID:${currentId}@gradwindow`);
  expect(calendar).not.toContain(pendingId);
  expect(calendar.match(/BEGIN:VEVENT/g)).toHaveLength(1);
});

test("homepage loads the tracker without runtime errors", async ({ page }) => {
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));

  await openTracker(page);

  await expect(page).toHaveTitle(/Global Top-200 Master's Applications/);
  await expect(
    page.locator("#application-groups .application-table").first(),
  ).toBeVisible();
  await expect(page.locator("#monitoring-health")).toContainText(
    /adapters healthy|Monitoring delayed/,
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

test("All universities lists schools in rank order with mixed window statuses", async ({
  page,
}) => {
  await openTracker(page);
  const all = page.locator('.status-tab[data-status="all"]');
  await expect(
    page.locator(".primary-status-tabs .status-tab").first(),
  ).toHaveAttribute("data-status", "all");
  await all.click();
  await expect(all).toHaveAttribute("aria-selected", "true");
  await expect(page).toHaveURL(/status=all/);
  const rows = page.locator(".window-card-row[data-school-id]");
  await expect(rows).toHaveCount(20);
  const ranks = await rows.locator(".rank-cell").allTextContents();
  const positions = ranks.map((rank) => Number(rank.replace(/\D/g, "")));
  expect(positions).toEqual([...positions].sort((a, b) => a - b));
  await expect(page.locator(".university-table")).toHaveCount(0);
  await expect(
    page
      .locator(".school-without-windows:not(.catalogue-group-parent)")
      .first(),
  ).toContainText("No verified application windows");
  await expect(
    page.locator(".school-without-windows").first().locator("td").nth(4),
  ).toHaveText("—");
  const allHeaders = await page
    .locator(".application-table th")
    .allTextContents();
  await expect(page.locator("#application-groups")).toContainText("Open now");
  await expect(page.locator("#application-groups")).toContainText(
    /Opening soon|Future/,
  );
  const schoolGroup = page
    .locator(".university-group-parent:not(.catalogue-group-parent)")
    .first();
  await expect(schoolGroup).toHaveClass(/university-group-parent--collapsed/);
  await schoolGroup.locator(".university-group-toggle").click();
  await expect(schoolGroup).toHaveAttribute("data-group-state", "expanded");
  await expect(page.locator(".university-group-child").first()).toBeVisible();
  await expect(
    page.locator(".university-group-child .calendar-menu-trigger").first(),
  ).toBeVisible();
  await page.locator("#collapse-visible-groups").click();
  await expect(page.locator(".university-group-child")).toHaveCount(0);
  await page.locator("#application-groups").scrollIntoViewIfNeeded();
  await page.screenshot({ path: "test-results/all-schools-desktop.png" });
  await expect(page.locator("#results-school-count")).toHaveAttribute(
    "data-count",
    await page.locator("#count-all").innerText(),
  );
  await page.reload();
  await expect(all).toHaveAttribute("aria-selected", "true");
  await expect(rows).toHaveCount(20);
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(all).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.locator("#application-groups").scrollIntoViewIfNeeded();
  await page.screenshot({ path: "test-results/all-schools-mobile.png" });
  await page.locator("#ranking-filter").selectOption("the");
  await expect(page).toHaveURL(/ranking=the/);
  await expect(rows).toHaveCount(20);
  await page.locator("#saved-status-tab").click();
  await expect(page.locator("#saved-status-tab")).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await expect(rows).toHaveCount(0);
  await page.locator('.status-tab[data-status="open"]').click();
  await expect(rows).toHaveCount(0);
  const openHeaders = await page
    .locator(".application-table")
    .first()
    .locator("th")
    .allTextContents();
  expect(
    allHeaders.map((label) => label.replace(/QS|THE/g, "Ranking")),
  ).toEqual(openHeaders.map((label) => label.replace(/QS|THE/g, "Ranking")));
});

test("favorite and calendar share one column with equal widths", async ({
  page,
}) => {
  await openTracker(page);
  const actions = page
    .locator(".application-actions")
    .filter({ has: page.locator(".calendar-menu") })
    .first();
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 900 });
    const favorite = actions.locator(".favorite-button");
    const calendar = actions.locator(".calendar-menu-trigger");
    const deadline = actions.locator("xpath=ancestor::tr").locator("td").nth(5);
    const programme = actions
      .locator("xpath=ancestor::tr")
      .locator("td")
      .nth(2);
    await expect(programme.locator(".application-action-summary")).toHaveText(
      "Verified exact dates",
    );
    await expect(programme.locator(".date-secondary")).toHaveText(
      /^[^·]+ [0-9]{4}$/,
    );
    await expect(programme.locator(".application-trust-summary")).toHaveCount(
      0,
    );
    await expect(programme).not.toContainText(
      /Open now|Deadline|days left|Application period|Check passed|Verified on/,
    );
    await expect(deadline.locator(".date-primary")).toHaveCount(1);
    await expect(deadline.locator(".date-primary")).toBeVisible();
    await expect(deadline).not.toContainText(" – ");
    await expect(favorite).toBeVisible();
    const favoriteBox = await favorite.boundingBox();
    const calendarBox = await calendar.boundingBox();
    expect(calendarBox.y).toBeGreaterThanOrEqual(
      favoriteBox.y + favoriteBox.height,
    );
    expect(Math.abs(calendarBox.width - favoriteBox.width)).toBeLessThan(1);
    expect(Math.abs(calendarBox.x - favoriteBox.x)).toBeLessThan(1);
    await calendar.click();
    await expect(actions.locator(".calendar-menu")).toHaveAttribute("open", "");
    await calendar.click();
    await favorite.scrollIntoViewIfNeeded();
    await page.screenshot({
      path: `test-results/stacked-actions-${width}.png`,
    });
  }
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
  await page.locator("#date-type-filter").selectOption("estimated");
  await expect(page).toHaveURL(/dates=estimated/);
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
