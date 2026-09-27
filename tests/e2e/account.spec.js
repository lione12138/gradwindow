import { expect, test } from "@playwright/test";

test("direct personal homepage entry opens login", async ({ page }) => {
  await page.goto("/#my-account");
  await page
    .getByRole("button", { name: "Sign in / create account", exact: true })
    .click();
  await expect(page.locator("#auth-panel")).toBeVisible();
  await expect(page.locator("#auth-password")).toBeVisible();
});

async function accountFixture(page) {
  let favorites = [];
  const requests = [];
  const user = {
    id: "test-account",
    displayName: "Lin",
    targetIntake: "2027 秋季",
    country: "中国",
  };
  await page.addInitScript(() => {
    localStorage.setItem("gradwindow:language", "zh");
    Object.defineProperty(window, "GRADWINDOW_CONFIG", {
      get: () => ({ roadmapUrl: "https://account.test" }),
      set: () => {},
    });
  });
  await page.route("https://static.cloudflareinsights.com/**", (route) =>
    route.abort(),
  );
  await page.route("https://account.test/**", async (route) => {
    const request = route.request();
    if (request.method() === "OPTIONS")
      return route.fulfill({
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Headers": "*",
          "Access-Control-Allow-Methods": "GET,POST,PUT,PATCH",
        },
      });
    const path = new URL(request.url()).pathname;
    const body = request.postDataJSON();
    requests.push({ path, body });
    if (path === "/me/favorites") favorites = body.favorites;
    if (path === "/me" && request.method() === "PATCH")
      Object.assign(user, body);
    await route.fulfill({
      json: { ok: true, user, token: "test-session", favorites },
      headers: { "Access-Control-Allow-Origin": "*" },
    });
  });
  await page.goto("/");
  await expect(page.locator("#results-school-count")).toHaveAttribute(
    "data-count",
    /\d+/,
  );
  const saved = await page.evaluate(async () => {
    const version = new URL(document.querySelector('script[src*="app.js"]').src)
      .search;
    const { state } = await import(`/state.js${version}`);
    const record = state.data.find(
      (item) =>
        item.dataStatus === "official" && item.trustStatus === "current",
    );
    return [`window:${record.id}`, `university:${record.universityId}`];
  });
  favorites = saved;
  return { requests, saved };
}

test("password login opens personal home, persists removal and clears private view on logout", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const fixture = await accountFixture(page);
  await page.locator("#auth-toggle").click();
  await page.locator("#auth-email").fill("user@example.com");
  await page.locator("#auth-password").fill("my memorable password 123");
  await page.locator("#auth-request-button").click();
  await expect(page.locator("#my-account")).toBeVisible();
  await expect(page.locator("#my-account h1")).toHaveText("我的申请主页");
  await expect(page.locator(".account-saved-project")).toHaveCount(1);
  await expect(page.locator(".account-saved-school")).toHaveCount(1);
  await page.screenshot({
    path: "test-results/account-desktop.png",
    fullPage: true,
  });
  await expect(page.locator(".account-calendar-grid .account-day")).toHaveCount(
    new Date(new Date().getFullYear(), new Date().getMonth() + 1, 0).getDate(),
  );
  await page.getByRole("button", { name: "下个月", exact: true }).click();
  await page.getByRole("button", { name: "今天", exact: true }).click();
  await page.locator(".account-saved-school button").click();
  await expect(page.locator(".account-saved-school")).toHaveCount(0);
  await expect
    .poll(
      () =>
        fixture.requests.filter((item) => item.path === "/me/favorites").at(-1)
          ?.body.favorites,
    )
    .toEqual([fixture.saved[0]]);
  await page.reload();
  await expect(page.locator(".account-saved-project")).toHaveCount(1);
  await expect(page.locator(".account-saved-school")).toHaveCount(0);
  await page
    .getByRole("button", { name: "账号设置", exact: true })
    .first()
    .click();
  await page.locator("#auth-logout-button").click();
  await page.locator(".auth-card button[data-auth-close]").click();
  await expect(page.locator("#my-account")).toContainText(
    "登录后查看你的个人主页",
  );
  await expect(page.locator(".account-saved-project")).toHaveCount(0);
  expect(errors).toEqual([]);
});

test("password reset verifies ownership, and failed sync survives a reload", async ({
  page,
}) => {
  await accountFixture(page);
  await page.locator("#auth-toggle").click();
  await page.locator('[data-auth-mode="reset"]').click();
  await page.locator("#auth-email").fill("user@example.com");
  await page.locator("#auth-password").fill("Abcd12");
  await page.locator("#auth-password-confirm").fill("Abcd12");
  await page.locator("#auth-request-button").click();
  await page.locator("#auth-code").fill("123456");
  await page.locator("#auth-verify-button").click();
  await expect(page.locator("#my-account")).toBeVisible();
  await expect(page.locator("#account-sync-status")).toContainText(
    "收藏会在你的设备之间同步",
  );
  await page.route("https://account.test/me/favorites", (route) =>
    route.fulfill({
      status: 503,
      json: { ok: false },
      headers: { "Access-Control-Allow-Origin": "*" },
    }),
  );
  await page.locator(".account-saved-school button").click();
  await expect(page.locator("#account-sync-status")).toContainText(
    "云端同步失败",
  );
  await page.reload();
  await expect(page.locator(".account-saved-project")).toHaveCount(1);
  await expect(page.locator(".account-saved-school")).toHaveCount(0);
  await expect(page.locator("#account-sync-status")).toContainText(
    "云端同步失败",
  );
});

test("registration checks password confirmation then verifies email, on mobile", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const fixture = await accountFixture(page);
  await page.locator('[data-mobile-nav="profile"]').click();
  await page.locator('[data-auth-mode="register"]').click();
  await page.locator("#auth-email").fill("new@example.com");
  await page.locator("#auth-password").fill("Abcd12");
  await page.locator("#auth-password-confirm").fill("Efgh34");
  await page.locator("#auth-request-button").click();
  await expect(page.locator("#auth-status")).toHaveText(
    "两次输入的密码不一致。",
  );
  await page.locator("#auth-password-confirm").fill("Abcd12");
  await page.locator("#auth-request-button").click();
  await expect(page.locator("#auth-verify-form")).toBeVisible();
  await page.locator("#auth-code").fill("123456");
  await page.locator("#auth-verify-button").click();
  await expect(page.locator("#my-account h1")).toHaveText("我的申请主页");
  expect(
    fixture.requests.find((item) => item.path === "/auth/verify").body,
  ).toEqual({
    email: "new@example.com",
    code: "123456",
    password: "Abcd12",
  });
  await expect(page.locator(".account-calendar")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/account-mobile.png",
    fullPage: true,
  });
  await page.locator('[data-mobile-nav="tracker"]').click();
  await expect(page.locator("#my-account")).toBeHidden();
  await expect(page.locator("#application-board")).toBeVisible();
});

test("personal calendar excludes predicted, unreviewed and other users' records", async ({
  page,
}) => {
  await accountFixture(page);
  const result = await page.evaluate(async () => {
    const { personalEvents } = await import("/account.js");
    const base = {
      universityId: "school-a",
      opensAt: "2026-09-01",
      closesAt: "2026-12-01",
    };
    return personalEvents(
      [
        { ...base, id: "official", dataStatus: "official" },
        { ...base, id: "predicted", dataStatus: "predicted" },
        { ...base, id: "review", trustStatus: "stale" },
        { ...base, id: "other", universityId: "school-b" },
      ],
      new Set(["university:school-a"]),
    ).map((event) => event.record.id);
  });
  expect(result).toEqual(["official", "official"]);
});
