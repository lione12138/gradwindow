import { expect, test } from "@playwright/test";
import { readFile } from "node:fs/promises";

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
  const imperial = rows.filter({
    has: page.getByRole("link", {
      name: "Imperial College London",
      exact: true,
    }),
  });
  await expect(imperial).toContainText("International applicants eligible");
  await expect(imperial.locator("time").last()).toHaveAttribute(
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
  const ranks = (await table.locator("tbody .rank-cell").allTextContents()).map(
    (rank) => Number(rank.replace(/^[#=]/, "")),
  );
  expect(ranks).toEqual([...ranks].sort((a, b) => a - b));
  await page.getByRole("button", { name: "Next page" }).click();
  await page.locator("#undergraduate-region").selectOption("Europe");
  await expect(
    page.getByRole("button", { name: "Previous page" }),
  ).toBeDisabled();
  await expect(
    table.getByRole("link", { name: "Harvard University", exact: true }),
  ).toHaveCount(0);
  await page.locator("#undergraduate-search").fill("UCL");
  await expect(table.locator("tbody tr")).toHaveCount(1);
  await page
    .getByRole("button", { name: "Expand schools on this page" })
    .click();
  await expect(table.locator(".university-group-child")).toHaveCount(2);
  await page.getByRole("button", { name: "Collapse all" }).click();
  await expect(table.locator(".university-group-child")).toHaveCount(0);
});

test("mobile undergraduate pagination keeps all windows for each school together", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/undergraduate.html");
  const response = await page.request.get(
    "/data/undergraduate-applications.json",
  );
  const records = await response.json();
  const schools = new Set(records.map(({ school }) => school));
  const table = page.locator(".undergraduate-table");
  const schoolLinks = table.locator(
    "tbody tr:not(.university-group-child) .school-link",
  );
  const range = page.locator(".pagination-summary");
  const previous = page.getByRole("button", { name: "Previous page" });
  const next = page.getByRole("button", { name: "Next page" });

  await expect(previous).toBeDisabled();
  await expect(schoolLinks).toHaveCount(20);
  await page
    .getByRole("button", { name: "Expand schools on this page" })
    .click();
  await expect(table.locator(".university-group-child").first()).toBeVisible();
  await expect(schoolLinks).toHaveCount(20);
  await expect(range).toHaveText(`1-20 / ${schools.size}`);

  const seen = [];
  for (let offset = 0; offset < schools.size; offset += 20) {
    const end = Math.min(offset + 20, schools.size);
    await expect(range).toHaveText(`${offset + 1}-${end} / ${schools.size}`);
    await expect(schoolLinks).toHaveCount(end - offset);
    seen.push(...(await schoolLinks.allTextContents()));
    if (end < schools.size) await next.click();
  }
  expect(seen).toHaveLength(schools.size);
  expect(new Set(seen)).toEqual(schools);
  await expect(next).toBeDisabled();
  await expect(page.locator(".group-heading h3")).toBeFocused();
  await previous.click();
  await expect(schoolLinks).toHaveCount(20);
  await expect(table.locator(".university-group-child")).toHaveCount(0);
  await page.getByRole("button", { name: "Switch language" }).click();
  await expect(page.getByRole("button", { name: "下一页" })).toBeEnabled();
  await page.locator("#undergraduate-search").fill("EDHEC");
  await expect(schoolLinks).toHaveCount(1);
  await expect(range).toHaveCount(0);
  await page.locator("#undergraduate-search").clear();
  await expect(range).toHaveText(`1-20 / ${schools.size}`);
});

test("UCAS windows show the submission dates and the official application route", async ({
  page,
}) => {
  await page.clock.setFixedTime(new Date("2026-11-21T12:00:00Z"));
  await page.goto("/undergraduate.html");
  await page.locator("#undergraduate-search").fill("University of Bath");
  await page.getByRole("button", { name: /Open now/ }).click();
  const row = page.locator(".undergraduate-window-row");
  await expect(row).toHaveCount(1);
  await expect(row.getByText(/UCAS equal consideration/)).toBeVisible();
  await expect(row.locator('time[datetime="2026-09-01"]')).toBeVisible();
  await expect(row.locator('time[datetime="2027-01-13"]')).toBeVisible();
  await expect(
    row.getByRole("link", { name: "Apply ↗", exact: true }),
  ).toHaveAttribute(
    "href",
    "https://www.bath.ac.uk/guides/applying-for-an-undergraduate-course/",
  );
  await expect(
    row.getByRole("link", { name: "Official dates ↗" }),
  ).toHaveAttribute("href", /bath\.ac\.uk\/corporate-information\//);
  await expect(
    row.getByRole("link", { name: "Submission dates ↗" }),
  ).toHaveAttribute("href", /ucas\.com\/events\//);
});

test("a UCAS deadline can be added to Google Calendar or Outlook", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1600, height: 900 });
  await page.goto("/undergraduate.html");
  await page.locator("#undergraduate-search").fill("University of Bath");
  const row = page.locator(".undergraduate-window-row");
  await expect(
    row.getByText("UCAS equal-consideration deadline"),
  ).toBeVisible();
  await row.locator(".calendar-menu-trigger").click();
  const googleLink = row.getByRole("link", { name: "Google Calendar" });
  await expect(googleLink).toBeInViewport();
  const google = new URL(await googleLink.getAttribute("href"));
  expect(google.searchParams.get("text")).toContain(
    "UCAS equal-consideration deadline",
  );
  expect(google.searchParams.get("dates")).toBe("20270113/20270114");
  expect(google.searchParams.get("details")).toContain("Fall 2027");
  expect(google.searchParams.get("details")).toContain(
    "https://www.bath.ac.uk/guides/applying-for-an-undergraduate-course/",
  );
  expect(google.searchParams.get("details")).toContain(
    "https://www.bath.ac.uk/corporate-information/",
  );
  const outlook = new URL(
    await row
      .getByRole("link", { name: "Outlook Calendar" })
      .getAttribute("href"),
  );
  expect(outlook.searchParams.get("allday")).toBe("true");
  expect(outlook.searchParams.get("startdt")).toBe("2027-01-13T00:00:00Z");
  expect(outlook.searchParams.get("subject")).toBe(
    google.searchParams.get("text"),
  );
});

test("mobile visitors can download a Chinese undergraduate calendar event", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/undergraduate.html");
  await page.getByRole("button", { name: "Switch language" }).click();
  await page.locator("#undergraduate-search").fill("巴斯大学");

  const row = page.locator(".undergraduate-window-row");
  const calendar = row.locator(".calendar-menu-trigger");
  await expect(calendar).toHaveAccessibleName("添加日历");
  await calendar.click();
  const downloadButton = row.getByRole("button", { name: "下载 ICS 日历文件" });
  const downloadPromise = page.waitForEvent("download");
  await downloadButton.click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe(
    "university-of-bath-standard-ucas-2027-equal-consideration-deadline.ics",
  );
  const contents = await readFile(await download.path(), "utf8");
  expect(contents).toContain("DTSTART;VALUE=DATE:20270113");
  expect(contents).toContain("DTEND;VALUE=DATE:20270114");
  expect(contents).toMatch(/SUMMARY:巴斯大学 .*UCAS 同等审理截止日期/);
  expect(contents).toContain("具体截止时间和时区请以官网为准。");
  await expect(calendar).toBeFocused();
});

test("CUHK separates the Advance Offer Round from the Medicine deadline", async ({
  page,
}) => {
  await page.clock.setFixedTime(new Date("2026-11-21T12:00:00Z"));
  await page.goto("/undergraduate.html");
  await page
    .locator("#undergraduate-search")
    .fill("Chinese University of Hong Kong");
  await page.getByRole("button", { name: /Deadline passed/ }).click();

  const rows = page.locator(".undergraduate-window-row");
  await expect(rows).toHaveCount(1);
  await expect(rows.getByText(/Advance Offer Round/)).toBeVisible();
  await expect(rows.getByText(/excluding Medicine/)).toBeVisible();
  await expect(rows.locator('time[datetime="2026-11-12"]')).toBeVisible();

  await page.getByRole("button", { name: /Open now/ }).click();
  await page.locator(".university-group-toggle").click();
  const medicine = rows.filter({ hasText: "Medicine MBChB" });
  await expect(medicine.getByText(/Regular Round/)).toBeVisible();
  await expect(medicine.locator('time[datetime="2026-10-02"]')).toBeVisible();
  await expect(medicine.locator('time[datetime="2027-01-07"]')).toBeVisible();
});

test("KAIST windows distinguish spring and fall undergraduate admissions", async ({
  page,
}) => {
  await page.clock.setFixedTime(new Date("2026-11-21T12:00:00Z"));
  await page.goto("/undergraduate.html");
  await page.locator("#undergraduate-search").fill("KAIST");
  const intake = page.locator("#undergraduate-intake");
  const rows = page.locator(".undergraduate-window-row");

  await intake.selectOption("Spring 2027");
  await expect(rows).toHaveCount(1);
  await expect(rows.getByText("Spring 2027 · Early Round")).toBeVisible();
  await expect(rows.locator('time[datetime="2026-10-22"]')).toBeVisible();

  await intake.selectOption("Fall 2027");
  await page.getByRole("button", { name: /Open now/ }).click();
  await expect(rows).toHaveCount(1);
  await expect(rows.getByText("Fall 2027 · Regular Round")).toBeVisible();
  await expect(rows.locator('time[datetime="2026-11-10"]')).toBeVisible();
  await expect(rows.locator('time[datetime="2027-01-14"]')).toBeVisible();
});

test("Helsinki keeps the SAT or ACT and diploma application windows separate", async ({
  page,
}) => {
  await page.clock.setFixedTime(new Date("2027-01-06T12:00:00Z"));
  await page.goto("/undergraduate.html");
  await page.locator("#undergraduate-search").fill("University of Helsinki");

  const rows = page.locator(".undergraduate-window-row");
  await page.getByRole("button", { name: /Open now/ }).click();
  await expect(rows).toHaveCount(1);
  await expect(rows.getByText(/Admission Group 1, SAT or ACT/)).toBeVisible();
  await expect(rows.locator('time[datetime="2027-01-05"]')).toBeVisible();
  await expect(rows.locator('time[datetime="2027-01-19"]')).toBeVisible();

  await page.getByRole("button", { name: /Future/ }).click();
  await expect(rows).toHaveCount(1);
  await expect(
    rows.getByText(/Admission Group 2, eligible diploma/),
  ).toBeVisible();
  await expect(rows.locator('time[datetime="2027-03-09"]')).toBeVisible();
  await expect(rows.locator('time[datetime="2027-03-23"]')).toBeVisible();
  await expect(
    rows.getByRole("link", { name: "International eligibility ↗" }),
  ).toHaveAttribute(
    "href",
    /helsinki\.fi\/.+\/required-application-enclosures$/,
  );
});

test("French bachelor rounds show their own deadlines in both languages", async ({
  page,
}) => {
  await page.clock.setFixedTime(new Date("2026-11-21T12:00:00Z"));
  await page.goto("/undergraduate.html");
  await page
    .locator("#undergraduate-search")
    .fill("Institut Polytechnique de Paris");
  await page.locator(".university-group-toggle").click();

  const rows = page.locator(".undergraduate-window-row");
  await expect(rows).toHaveCount(3);
  const thirdRound = rows.filter({
    has: page.locator('time[datetime="2027-02-08"]'),
  });
  await expect(thirdRound.getByText("Fall 2027 · Third round")).toBeVisible();
  await expect(thirdRound.locator('time[datetime="2027-01-07"]')).toBeVisible();

  await page.getByRole("button", { name: "Switch language" }).click();
  await expect(thirdRound.getByText("2027 年秋季 · 第三轮")).toBeVisible();
});

test("EDHEC shows the later international BBA rounds with their own dates", async ({
  page,
}) => {
  await page.goto("/undergraduate.html");
  await page.locator("#undergraduate-search").fill("EDHEC");
  await page.locator(".university-group-toggle").click();
  const rows = page.locator(".undergraduate-window-row");
  await expect(rows).toHaveCount(5);

  const fourthRound = rows.filter({ hasText: "Fourth round" });
  await expect(
    fourthRound.locator('time[datetime="2027-02-16"]'),
  ).toBeVisible();
  await expect(
    fourthRound.locator('time[datetime="2027-04-01"]'),
  ).toBeVisible();

  await page.getByRole("button", { name: "Switch language" }).click();
  const fifthRound = rows.filter({ hasText: "第五轮" });
  await expect(fifthRound.locator('time[datetime="2027-04-06"]')).toBeVisible();
  await expect(fifthRound.locator('time[datetime="2027-06-08"]')).toBeVisible();
});
