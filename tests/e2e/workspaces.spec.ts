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
  await expect.poll(() => new URL(page.url()).searchParams.get("module")).toBe("Bond Pricing");
  await page.getByRole("button", { name: "Options & Greeks", exact: true }).click();
  await expect.poll(() => new URL(page.url()).searchParams.get("module")).toBe("Options & Greeks");
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


test("Historical Market Explorer keeps its controls and graph compact", async ({ page }) => {
  await mockMarketApi(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Historical Market Explorer", exact: true }).click();

  await expect(page.getByText("Historical market explorer", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Dataset")).toBeVisible();
  await expect(page.getByLabel("Currency pair")).toBeVisible();
  await expect(page.getByLabel("From date")).toBeVisible();
  await expect(page.getByLabel("To date")).toBeVisible();
  await expect(page.getByPlaceholder("Type to filter")).toBeVisible();
  await expect(page.locator(".explorer-chart-panel .recharts-surface")).toBeVisible();
  await expect(page.locator(".explorer-records-panel .data-table tbody tr").first()).toBeVisible();

  const desktopLayout = await page.locator(".explorer-results-grid").evaluate(element => {
    const chart = element.querySelector(".explorer-chart-panel")!.getBoundingClientRect();
    const records = element.querySelector(".explorer-records-panel")!.getBoundingClientRect();
    const table = element.querySelector(".explorer-table-wrap")!;
    const style = getComputedStyle(table);
    return {
      sideBySide: records.left >= chart.right - 2,
      contained: style.overflowY === "auto" && style.maxHeight !== "none",
    };
  });
  expect(desktopLayout.sideBySide).toBe(true);
  expect(desktopLayout.contained).toBe(true);

  await page.getByLabel("Currency pair").selectOption("USD/KES");
  await expect(page.locator(".explorer-result-meta")).toContainText("100 records");
  await page.getByRole("button", { name: "Reset filters" }).click();
  await expect(page.getByLabel("Currency pair")).toHaveValue("All");

  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole("tab", { name: "Chart" })).toBeVisible();
  await expect(page.locator(".explorer-chart-panel")).toBeVisible();
  await page.getByRole("tab", { name: /Records/ }).click();
  await expect(page.locator(".explorer-records-panel")).toBeVisible();
  await expect(page.locator(".explorer-chart-panel")).not.toBeVisible();
});


test("module controls change the calculations and data views", async ({ page }) => {
  const pageErrors: string[] = [];
  page.on("pageerror", error => pageErrors.push(error.message));
  await mockMarketApi(page);
  await page.goto("/");

  // Kenyan Market: changing the pair changes the quoted series.
  await page.getByRole("button", { name: "Kenyan Market", exact: true }).click();
  await page.getByLabel("Currency pair").selectOption("GBP/KES");
  await expect(page.locator(".explorer-chart-panel .recharts-surface")).toHaveCount(0);
  await expect(page.locator(".data-table tbody tr").first()).toContainText("GBP/KES");

  // Treasury Bills: tenor selection and purchase value respond to inputs.
  await page.getByRole("button", { name: "Treasury Bills", exact: true }).click();
  await page.getByLabel("Bill maturity").selectOption("182");
  const purchaseMetric = page.locator(".metric-card").filter({ hasText: "Estimated purchase price" }).locator(".metric-value");
  const priceBefore = await purchaseMetric.textContent();
  await page.getByLabel("Face value (KES)").fill("200000");
  await expect(purchaseMetric).not.toHaveText(priceBefore || "");
  await page.setViewportSize({ width: 390, height: 844 });
  const kpiFits = await page.locator(".treasury-kpi-grid").evaluate(element => {
    const parent = element.getBoundingClientRect();
    const cards = [...element.querySelectorAll(".metric-card")].map(card => card.getBoundingClientRect());
    return cards.every(card => card.left >= parent.left - 1 && card.right <= parent.right + 1);
  });
  expect(kpiFits).toBe(true);
  await expect(page.locator(".treasury-chart .recharts-surface")).toBeVisible();

  // Bond Pricing: coupon and frequency affect the valuation and payment graph.
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.getByRole("button", { name: "Bond Pricing", exact: true }).click();
  const bondPriceMetric = page.locator(".metric-card").filter({ hasText: "Model bond price" }).locator(".metric-value");
  const bondPriceBefore = await bondPriceMetric.textContent();
  await page.getByLabel("Annual coupon rate (%)").fill("10");
  await expect(bondPriceMetric).not.toHaveText(bondPriceBefore || "");
  await page.getByLabel("Payments per year").selectOption("4");
  await expect.poll(() => page.locator(".bond-cashflow-chart .recharts-bar-rectangle").count()).toBeGreaterThanOrEqual(20);
  await expect(page.locator(".bond-price-chart .recharts-line")).toBeVisible();

  // Options & Greeks: option type changes the theoretical value and sensitivities.
  await page.getByRole("button", { name: "Options & Greeks", exact: true }).click();
  const optionMetric = page.locator(".metric-card").filter({ hasText: "Call model value" }).locator(".metric-value");
  const callValue = await optionMetric.textContent();
  await page.getByLabel("Option type").selectOption("Put");
  const putMetric = page.locator(".metric-card").filter({ hasText: "Put model value" }).locator(".metric-value");
  await expect(putMetric).not.toHaveText(callValue || "");

  // Risk Analysis: confidence level selects a different tail-loss estimate.
  await page.getByRole("button", { name: "Risk Analysis", exact: true }).click();
  await page.getByLabel("Confidence level").selectOption("99");
  await expect(page.getByText("Historical VaR · 99%", { exact: true })).toBeVisible();
  await expect(page.locator(".recharts-bar-rectangle").first()).toBeVisible();

  // Portfolio Intelligence: KES position values recalculate total capital.
  await page.getByRole("button", { name: "Portfolio Intelligence", exact: true }).click();
  await page.getByLabel("Government bond value (KES)").fill("250000");
  const totalMetric = page.locator(".metric-card").filter({ hasText: "Portfolio value" }).locator(".metric-value");
  await expect(totalMetric).toContainText("1,100,000");
  await page.getByLabel("Government bond volatility (%)").fill("120");
  await expect(page.getByText(/valid return and volatility assumptions/i)).toBeVisible();

  // Portfolio: weights must balance to 100% before the basket is valued.
  await page.getByRole("button", { name: "Portfolio", exact: true }).click();
  await page.getByLabel("USD/KES weight (%)").fill("50");
  await expect(page.getByText(/totalling exactly 100%/i)).toBeVisible();
  await page.getByLabel("GBP/KES weight (%)").fill("20");
  await expect(page.getByText("Total allocation: 100.00%", { exact: false })).toBeVisible();
  await expect(page.locator(".recharts-area")).toBeVisible();

  // Backtesting: the Treasury bill strategy has its own signal and lookback.
  await page.getByRole("button", { name: "Backtesting", exact: true }).click();
  await page.getByLabel("Backtest mode").selectOption("Treasury bill yield momentum");
  await page.getByLabel("Yield-momentum lookback").fill("5");
  await expect(page.getByText("Strategy cumulative return", { exact: true })).toBeVisible();
  await expect(page.locator(".recharts-line").first()).toBeVisible();

  // Stress Testing: input shocks update monetary P/L and invalid rates are safely rejected.
  await page.getByRole("button", { name: "Stress Testing", exact: true }).click();
  const pnlMetric = page.locator(".metric-card").filter({ hasText: "Profit / loss" }).locator(".metric-value");
  const pnlBefore = await pnlMetric.textContent();
  await page.getByLabel("Market shock (%)").fill("-20");
  await expect(pnlMetric).not.toHaveText(pnlBefore || "");
  await page.getByLabel("Current Treasury bill yield (%)").fill("150");
  await expect(page.getByText(/Check all fixed-income inputs/i)).toBeVisible();
  await page.getByLabel("Current Treasury bill yield (%)").fill("9");
  await expect(page.getByText("CBK +50 bps", { exact: false })).toHaveCount(0);

  // Research Intelligence: changing moving-average windows updates its trend study.
  await page.getByRole("button", { name: "Research Intelligence", exact: true }).click();
  await page.getByLabel("Short window").fill("5");
  await page.getByLabel("Long window").fill("15");
  await expect(page.locator(".recharts-line")).toHaveCount(3);

  expect(pageErrors, "Input changes must not cause uncaught browser errors").toEqual([]);
});

test("financial report exports have the expected formats and platform heading", async ({ page }) => {
  await mockMarketApi(page);
  await page.route("**/api/report", route => route.fulfill({
    status: 200,
    headers: {
      "content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "content-disposition": 'attachment; filename="Kenya_Financial_Analytics_Market_Report.xlsx"',
    },
    body: Buffer.from("PK\\u0003\\u0004KFA report fixture"),
  }));
  await page.goto("/");
  await page.getByRole("button", { name: "Financial Reports", exact: true }).click();

  const [workbook] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "Download formatted Excel" }).click(),
  ]);
  expect(workbook.suggestedFilename()).toBe("Kenya_Financial_Analytics_Market_Report.xlsx");

  const [summary] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "Executive summary CSV" }).click(),
  ]);
  expect(summary.suggestedFilename()).toBe("KFA_Executive_Summary.csv");

  const [history] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "Full history CSV" }).click(),
  ]);
  expect(history.suggestedFilename()).toBe("KFA_Full_Market_History.csv");
});
