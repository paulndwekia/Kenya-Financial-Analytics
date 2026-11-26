import { test, expect, type Page } from "@playwright/test";

const MODULES = [
  "Dashboard",
  "Kenyan Market",
  "Market Intelligence",
  "Yield Curve",
  "Treasury Bills",
  "Bond Pricing",
  "Options & Greeks",
  "Backtesting",
  "Risk Analysis",
  "Risk Intelligence",
  "Stress Testing",
  "Portfolio Intelligence",
  "Portfolio",
  "Historical Market Explorer",
  "Research Intelligence",
  "Financial Reports",
];

function marketFixture() {
  const pairs = [
    { instrument: "USD/KES", base: 129.1, drift: 0.013 },
    { instrument: "GBP/KES", base: 168.2, drift: 0.018 },
    { instrument: "EUR/KES", base: 141.6, drift: 0.011 },
  ];
  const fx = [];
  const start = new Date("2026-07-01T00:00:00Z");
  for (let i = 0; i < 100; i++) {
    const date = new Date(start);
    date.setUTCDate(start.getUTCDate() + i);
    const dateLabel = date.toISOString().slice(0, 10);
    for (let p = 0; p < pairs.length; p++) {
      const pair = pairs[p];
      const value = pair.base + pair.drift * i + Math.sin(i / (4 + p)) * (0.12 + p * 0.025);
      fx.push({
        date: dateLabel,
        instrument: pair.instrument,
        value: Number(value.toFixed(4)),
        source: "Central Bank of Kenya",
        source_url: "https://www.centralbank.go.ke/new-rates/",
      });
    }
  }

  const bills = [];
  const tenors = [91, 182, 364];
  for (let i = 0; i < 16; i++) {
    const date = new Date("2026-08-04T00:00:00Z");
    date.setUTCDate(date.getUTCDate() + i * 7);
    const dateLabel = date.toISOString().slice(0, 10);
    for (const tenor of tenors) {
      const rate = 0.084 + tenor / 100000 + i * 0.00014 + Math.sin(i / 3) * 0.00035;
      bills.push({
        date: dateLabel,
        tenor_days: tenor,
        rate: Number(rate.toFixed(6)),
        price: Number((100 / (1 + rate * tenor / 365)).toFixed(4)),
        amount_offered: 10_000_000_000,
        amount_accepted: 8_500_000_000,
        issue_number: `TEST${String(i + 1).padStart(2, "0")}/${tenor}`,
        source: "Central Bank of Kenya",
        source_url: "https://www.centralbank.go.ke/",
      });
    }
  }
  const latestFx = fx.at(-1)?.date ?? null;
  const latestBill = bills.at(-1)?.date ?? null;
  return {
    ok: true,
    fx,
    bills,
    source: "Central Bank of Kenya",
    retrieved_at: new Date().toISOString(),
    health: {
      database: "Neon Postgres (test fixture)",
      database_connected: true,
      fx_rows: fx.length,
      bills_rows: bills.length,
      latest_fx_observation: latestFx,
      latest_bill_observation: latestBill,
      last_refresh: {
        source: "Playwright market-data fixture",
        status: "success",
        started_at: new Date().toISOString(),
        completed_at: new Date().toISOString(),
        fx_rows_upserted: fx.length,
        bill_rows_upserted: bills.length,
        details: {},
      },
      warnings: [],
    },
  };
}

async function mockMarketApi(page: Page) {
  const fixture = marketFixture();
  await page.route("**/api/market", route => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(fixture),
  }));
  await page.addInitScript(() => {
    localStorage.setItem("kfa-cookie-choice", "essential-only");
    localStorage.setItem("kfa-theme", "light");
  });
}

test("all 16 workspaces open from navigation and show their own analytical graph", async ({ page }) => {
  const pageErrors: string[] = [];
  page.on("pageerror", error => pageErrors.push(error.message));
  await mockMarketApi(page);
  await page.goto("/");
  await expect(page.locator(".status-pill")).toContainText("NEON DATABASE");

  for (const moduleName of MODULES) {
    await page.getByRole("button", { name: moduleName, exact: true }).click();
    await expect(page.locator(".page-title")).toHaveText(
      moduleName === "Dashboard" ? "Market overview" : moduleName
    );
    await expect(page.locator(".workspace-stack")).toBeVisible();
    await expect(page.locator(".recharts-surface").first()).toBeVisible();
  }
  expect(pageErrors, "No module should throw a browser-side error").toEqual([]);
});

test("module navigation is reflected in the address and browser history", async ({ page }) => {
  await mockMarketApi(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Bond Pricing", exact: true }).click();
  await expect(page).toHaveURL(/module=Bond(?:%20|\+)Pricing/);
  await page.getByRole("button", { name: "Options & Greeks", exact: true }).click();
  await expect(page).toHaveURL(/module=Options+%26+Greeks|module=Options%20%26%20Greeks/);
  await page.goBack();
  await expect(page.locator(".page-title")).toHaveText("Bond Pricing");
  await page.goBack();
  await expect(page.locator(".page-title")).toHaveText("Market overview");
});

test("the mobile drawer closes after choosing a workspace", async ({ page }) => {
  await mockMarketApi(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "Open navigation" }).click();
  await expect(page.locator(".sidebar")).toHaveClass(/open/);
  await page.getByRole("button", { name: "Financial Reports", exact: true }).click();
  await expect(page.locator(".page-title")).toHaveText("Financial Reports");
  await expect(page.locator(".sidebar")).not.toHaveClass(/open/);
});
