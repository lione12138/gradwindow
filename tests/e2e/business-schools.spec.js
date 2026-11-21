import { expect, test } from "@playwright/test";

test("visitors can find Paris-area undergraduate business programmes", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/undergraduate.html");
  await page.getByRole("link", { name: "Business schools" }).click();
  await expect(page).toHaveURL(/\/business-schools\.html$/);
  await page.getByLabel("Region", { exact: true }).selectOption("paris");
  await page.getByLabel("Degree level").selectOption("undergraduate");

  const schools = page.locator(".business-school:visible");
  await expect(schools).toHaveCount(4);
  await expect(page.getByText("INSEAD", { exact: true })).not.toBeVisible();
  await expect(
    page.getByRole("link", {
      name: /Bachelor in Data, Society and Organisations/,
    }),
  ).toHaveAttribute(
    "href",
    "https://www.hec.edu/en/bachelor-programs/admissions",
  );

  await page.getByRole("button", { name: "Switch language" }).click();
  await page.getByRole("searchbox").fill("塞尔吉");
  await expect(schools).toHaveCount(1);
  await expect(schools.getByRole("heading")).toHaveText("ESSEC 高等商学院");
  await expect(
    schools.getByRole("link", { name: /全球工商管理学士/ }),
  ).toBeVisible();
  await page.getByRole("searchbox").fill("无匹配");
  await expect(page.getByText("没有符合条件的商学院")).toBeVisible();
});
