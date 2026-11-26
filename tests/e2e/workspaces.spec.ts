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

async function mockMarketApi(page: Page, mutate?: (fixture: ReturnType<typeof marketFixture>) => void) {
  const fixture = marketFixture();
  mutate?.(fixture);
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

test("dashboard provides a distinct market overview and truthful import status", async ({ page }) => {
  await mockMarketApi(page);
  await page.goto("/");
  await expect(page.locator(".dashboard-quote-card")).toHaveCount(3);
  await expect(page.locator(".dashboard-quote-card").nth(0)).toContainText("USD/KES");
  await expect(page.locator(".dashboard-quote-card").nth(1)).toContainText("GBP/KES");
  await expect(page.locator(".dashboard-quote-card").nth(2)).toContainText("EUR/KES");
  await expect(page.locator(".dashboard-index-chart .recharts-line")).toHaveCount(3);
  await expect(page.getByText("All three tenors are available for this auction.")).toBeVisible();
  await expect(page.getByText("Latest import attempt", { exact: true })).toBeVisible();
  await expect(page.locator(".dashboard-health-item .health-good")).toContainText("Successful");

  await page.setViewportSize({ width: 390, height: 844 });
  const quoteCardsFit = await page.locator(".dashboard-quote-grid").evaluate(element => {
    const parent = element.getBoundingClientRect();
    const cards = [...element.querySelectorAll(".dashboard-quote-card")].map(card => card.getBoundingClientRect());
    return cards.every(card => card.left >= parent.left - 1 && card.right <= parent.right + 1);
  });
  expect(quoteCardsFit).toBe(true);
});

test("Kenyan Market isolates one FX pair and updates its chosen observation window", async ({ page }) => {
  await mockMarketApi(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Kenyan Market", exact: true }).click();

  await expect(page.locator(".market-detail-metrics .metric-card")).toHaveCount(5);
  await expect(page.locator(".market-detail-chart .recharts-surface")).toBeVisible();
  await expect(page.getByText("Kenyan shillings per one unit of foreign currency", { exact: false })).toBeVisible();

  await page.getByLabel("Currency pair").selectOption("GBP/KES");
  await expect(page.locator(".market-recent-table tbody tr").first()).toContainText("GBP/KES");
  await page.getByRole("button", { name: "30D", exact: true }).click();
  const thirtyDayMeta = await page.locator(".market-period-meta").textContent();
  await page.getByRole("button", { name: "All", exact: true }).click();
  await expect(page.locator(".market-period-meta")).toContainText("100 observations");
  expect(thirtyDayMeta).toContain("observations");
  expect(Number(thirtyDayMeta?.match(/(\d+) observations/)?.[1] || 0)).toBeLessThan(100);

  await page.setViewportSize({ width: 390, height: 844 });
  const metricsFit = await page.locator(".market-detail-metrics").evaluate(element => {
    const parent = element.getBoundingClientRect();
    const cards = [...element.querySelectorAll(".metric-card")].map(card => card.getBoundingClientRect());
    return cards.every(card => card.left >= parent.left - 1 && card.right <= parent.right + 1);
  });
  expect(metricsFit).toBe(true);
});

test("Market Intelligence compares momentum, volatility and aligned-date correlations", async ({ page }) => {
  await mockMarketApi(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Market Intelligence", exact: true }).click();

  await expect(page.locator(".intelligence-kpis .metric-card")).toHaveCount(4);
  await expect(page.locator(".intelligence-momentum-chart .recharts-bar-rectangle")).toHaveCount(3);
  await expect(page.locator(".intelligence-scatter-chart .recharts-scatter-symbol")).toHaveCount(3);
  await expect(page.locator(".correlation-matrix tbody tr")).toHaveCount(3);
  await expect(page.locator(".correlation-matrix tbody tr").first().locator("td")).toHaveCount(3);
  await expect(page.locator(".intelligence-ranking-table")).toContainText("20-observation move");

  await page.getByRole("button", { name: "5 obs.", exact: true }).click();
  await expect(page.locator(".intelligence-ranking-table")).toContainText("5-observation move");
  await page.getByRole("button", { name: "60 obs.", exact: true }).click();
  await expect(page.locator(".intelligence-ranking-table")).toContainText("60-observation move");

  await page.setViewportSize({ width: 390, height: 844 });
  const kpisFit = await page.locator(".intelligence-kpis").evaluate(element => {
    const parent = element.getBoundingClientRect();
    const cards = [...element.querySelectorAll(".metric-card")].map(card => card.getBoundingClientRect());
    return cards.every(card => card.left >= parent.left - 1 && card.right <= parent.right + 1);
  });
  expect(kpisFit).toBe(true);
  await expect(page.locator(".correlation-matrix-wrap")).toBeVisible();
});

test("Yield Curve uses one matched auction and presents an observed curve and forward-rate estimate", async ({ page }) => {
  await mockMarketApi(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Yield Curve", exact: true }).click();

  await expect(page.locator(".yield-curve-chart .recharts-surface")).toBeVisible();
  await expect(page.locator(".yield-curve-slope-table tbody tr")).toHaveCount(3);
  await expect(page.locator(".data-table").filter({ has: page.locator("th", { hasText: "Interpolated spot yield" }) }).locator("tbody tr")).toHaveCount(5);
  await expect(page.locator(".metric-card").filter({ hasText: "Implied simple forward rate" }).locator(".metric-value")).not.toHaveText("—");
  await expect(page.getByText(/same auction date/i).first()).toBeVisible();
});

test("Yield Curve does not extrapolate when the latest auction is missing a short tenor", async ({ page }) => {
  await mockMarketApi(page, fixture => {
    const latestDate = fixture.health.latest_bill_observation;
    fixture.bills = fixture.bills.filter(row => row.date !== latestDate || row.tenor_days !== 91);
  });
  await page.goto("/");
  await page.getByRole("button", { name: "Yield Curve", exact: true }).click();

  await expect(page.getByText("Partial curve · 2 of 3 matched tenors")).toBeVisible();
  const interpolationTable = page.locator(".data-table").filter({ has: page.locator("th", { hasText: "Interpolated spot yield" }) });
  await expect(interpolationTable.locator("tbody tr").nth(0)).toContainText("Not available");
  await expect(interpolationTable.locator("tbody tr").nth(1)).toContainText("Not available");
  await expect(page.locator(".metric-card").filter({ hasText: "Implied simple forward rate" }).locator(".metric-value")).toHaveText("—");

  await page.getByLabel("Forward period starts (days)").selectOption("182");
  await page.getByLabel("Forward period ends (days)").selectOption("364");
  await expect(page.locator(".metric-card").filter({ hasText: "Implied simple forward rate" }).locator(".metric-value")).not.toHaveText("—");

  await page.setViewportSize({ width: 390, height: 844 });
  const controlsFit = await page.locator(".yield-curve-workspace .control-row").last().evaluate(element => {
    const parent = element.getBoundingClientRect();
    const fields = [...element.querySelectorAll(".field")].map(field => field.getBoundingClientRect());
    return fields.every(field => field.left >= parent.left - 1 && field.right <= parent.right + 1);
  });
  expect(controlsFit).toBe(true);
});

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
  await expect(page.locator(".data-table").filter({ has: page.locator("th", { hasText: "Price basis" }) })).toContainText("CBK published");
  const investmentPrice = await purchaseMetric.textContent();
  await page.getByLabel("Pricing convention").selectOption("discount");
  await expect(purchaseMetric).not.toHaveText(investmentPrice || "");
  await expect(page.getByText("Equivalent discount rate", { exact: true })).toBeVisible();
  await page.getByLabel("Pricing convention").selectOption("investment");
  await page.getByLabel("Annual investment yield (%)").fill("120");
  await expect(page.getByText(/quote rate from 0% to 100%/i)).toBeVisible();
  await page.getByLabel("Annual investment yield (%)").fill("8.75");
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
  await expect(page.locator(".bond-cashflow-table tbody tr")).toHaveCount(20);
  await expect.poll(() => page.locator(".bond-cashflow-chart .recharts-bar-rectangle").count()).toBeGreaterThanOrEqual(5);
  await expect(page.locator(".bond-price-chart .recharts-line")).toHaveCount(2);
  await expect(page.locator(".bond-yield-readout")).toContainText("13.00%");

  // Bond schedules must land exactly on the contractual maturity date.
  await page.getByLabel("Years to maturity").fill("2.3");
  await expect(page.getByText(/Maturity must be an exact multiple/i)).toBeVisible();
  await expect(page.locator(".bond-price-chart .recharts-surface")).toHaveCount(0);
  await page.getByLabel("Years to maturity").fill("2.25");
  await expect(page.locator(".bond-cashflow-table tbody tr")).toHaveCount(9);

  // The yield graph follows the selected yield and includes the approximation comparison.
  await page.getByLabel("Yield to maturity (%)").fill("80");
  await expect(page.locator(".bond-price-chart .recharts-line")).toHaveCount(2);
  const currentPrice = await bondPriceMetric.textContent();
  await page.getByLabel("Yield change (basis points)").fill("250");
  const shockedMetric = page.locator(".metric-card").filter({ hasText: "Estimated shocked price" }).locator(".metric-value");
  const shockedBefore = await shockedMetric.textContent();
  await page.getByLabel("Yield change (basis points)").fill("-250");
  await expect(shockedMetric).not.toHaveText(shockedBefore || "");
  expect(currentPrice).not.toBe("");

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
  await expect(page.getByText("Total allocation: 110.00%", { exact: false })).toBeVisible();
  await expect(page.getByText(/weights totalling exactly 100%/i)).toBeVisible();
  await page.getByLabel("GBP/KES weight (%)").fill("20");
  await expect(page.getByText("Total allocation: 100.00%", { exact: false })).toBeVisible();
  await expect(page.locator(".recharts-area")).toBeVisible();

  // Historical Market Explorer: switch datasets, filter a tenor and export only matching records.
  await page.getByRole("button", { name: "Historical Market Explorer", exact: true }).click();
  await page.getByLabel("Dataset").selectOption("Treasury bills");
  await page.getByLabel("Bill tenor").selectOption("364");
  await expect(page.locator(".explorer-result-meta")).toContainText("16 records");
  const [filteredBills] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "Export filtered CSV" }).click(),
  ]);
  expect(filteredBills.suggestedFilename()).toBe("KFA_Treasury_Bill_Historical_Observations.csv");

  // Backtesting: the Treasury bill strategy has its own signal and lookback.
  await page.getByRole("button", { name: "Backtesting", exact: true }).click();
  await page.getByLabel("Backtest mode").selectOption("Treasury bill yield momentum");
  await page.getByLabel("Yield-momentum lookback").fill("5");
  await expect(page.getByText("Strategy cumulative return", { exact: true })).toBeVisible();
  await expect(page.locator(".workspace-stack:visible .recharts-line:visible").first()).toBeVisible();

  // Stress Testing: input shocks update monetary P/L and invalid rates are safely rejected.
  await page.getByRole("button", { name: "Stress Testing", exact: true }).click();
  const pnlMetric = page.locator(".metric-card").filter({ hasText: "Profit / loss" }).locator(".metric-value");
  const pnlBefore = await pnlMetric.textContent();
  await page.getByLabel("Market shock (%)").fill("-20");
  await expect(pnlMetric).not.toHaveText(pnlBefore || "");
  await page.getByLabel("Current Treasury bill yield (%)").fill("150");
  await expect(page.getByText(/Check all fixed-income inputs/i)).toBeVisible();
  await page.getByLabel("Current Treasury bill yield (%)").fill("9");
  await expect(page.getByText("CBK +50 bps", { exact: false })).toBeVisible();

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
  const stream = await history.createReadStream();
  if (!stream) throw new Error("The full-history CSV download did not create a readable file.");
  const chunks: Buffer[] = [];
  for await (const chunk of stream) chunks.push(Buffer.from(chunk));
  const csv = Buffer.concat(chunks).toString("utf8");
  expect(csv).toContain("Daily FX change (decimal)");
  expect(csv).toContain("USD/KES");
  expect(csv).toContain("Treasury bill");
});
