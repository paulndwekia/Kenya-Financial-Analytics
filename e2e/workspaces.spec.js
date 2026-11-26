const { test, expect } = require("@playwright/test");

const moduleChecks = [
  ["Dashboard", "USD / KES"],
  ["Kenyan Market", "Exchange-rate history"],
  ["Market Intelligence", "Currency comparison"],
  ["Yield Curve", "Latest recorded auction curve"],
  ["Treasury Bills", "Auction history by tenor"],
  ["Bond Pricing", "Fixed-rate bond valuation"],
  ["Options & Greeks", "Black–Scholes model"],
  ["Backtesting", "Moving-average strategy test"],
  ["Risk Analysis", "Historical FX risk"],
  ["Risk Intelligence", "Treasury yield risk overview"],
  ["Stress Testing", "Capital shock scenarios"],
  ["Portfolio Intelligence", "Relative performance"],
  ["Portfolio", "Currency exposure basket"],
  ["Historical Market Explorer", "Historical observation explorer"],
  ["Research Intelligence", "Moving-average research"],
  ["Financial Reports", "Market research report"],
];

function makeFixture() {
  const fx = [];
  const start = new Date("2026-06-01T00:00:00Z");
  for (let i = 0; i < 130; i += 1) {
    const date = new Date(start);
    date.setUTCDate(date.getUTCDate() + i);
    const day = date.toISOString().slice(0, 10);
    fx.push(
      { date: day, instrument: "USD/KES", value: 129 + i * 0.018 + Math.sin(i / 6) * 0.18, source: "CBK test fixture" },
      { date: day, instrument: "GBP/KES", value: 169 + i * 0.015 + Math.cos(i / 7) * 0.22, source: "CBK test fixture" },
      { date: day, instrument: "EUR/KES", value: 142 + i * 0.012 + Math.sin(i / 9) * 0.15, source: "CBK test fixture" },
    );
  }
  const bills = [];
  for (let i = 0; i < 14; i += 1) {
    const date = new Date("2026-09-01T00:00:00Z");
    date.setUTCDate(date.getUTCDate() + i * 7);
    const day = date.toISOString().slice(0, 10);
    for (const tenor of [91, 182, 364]) {
      const rate = 0.085 + tenor / 100000 + i * 0.00008;
      bills.push({
        date: day,
        tenor_days: tenor,
        rate,
        price: 100 / (1 + rate * tenor / 365),
        issue_number: String(2600 + i) + "/" + String(tenor).padStart(3, "0"),
        source: "CBK test fixture",
        source_url: "https://www.centralbank.go.ke/",
      });
    }
  }
  return {
    ok: true,
    fx,
    bills,
    source: "Central Bank of Kenya",
    retrieved_at: "2026-11-26T08:00:00Z",
    health: {
      database: "Neon Postgres test fixture",
      database_connected: true,
      fx_rows: fx.length,
      bills_rows: bills.length,
      latest_fx_observation: fx[fx.length - 1].date,
      latest_bill_observation: bills[bills.length - 1].date,
      last_refresh: {
        status: "success",
        source: "CBK test fixture",
        completed_at: "2026-11-26T08:00:00Z",
        fx_rows_upserted: fx.length,
        bill_rows_upserted: bills.length,
      },
      warnings: [],
    },
  };
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("kfa-cookie-choice", "essential-only");
    localStorage.setItem("kfa-theme", "light");
  });
  const fixture = makeFixture();
  await page.route("**/api/market", route =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(fixture),
    }),
  );
});

test("all 16 workspaces are distinct and sidebar navigation reaches each module", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".status-pill")).to_contain_text("NEON DATABASE");
  await expect(page.locator("aside .nav-item")).to_have_count(16);

  const seenTitles = new Set();
  for (const [name, expectedPanel] of moduleChecks) {
    await page.locator("aside .nav-item").filter({ hasText: name }).click();
    await expect(page.locator(".page-title")).to_have_text(name === "Dashboard" ? "Market overview" : name);
    await expect(page.locator(".workspace-stack .panel-title").first()).to_have_text(expectedPanel);
    seenTitles.add(await page.locator(".workspace-stack .panel-title").first().inner_text());
    if (name !== "Dashboard") {
      await expect(page).to_have_url(new RegExp("\\?module=" + encodeURIComponent(name)));
    }
  }
  expect(seenTitles.size).toBe(16);
});

test("module URLs work directly and browser back/forward restores the previous workspace", async ({ page }) => {
  await page.goto("/?module=Bond%20Pricing");
  await expect(page.locator(".page-title")).to_have_text("Bond Pricing");
  await page.locator("aside .nav-item").filter({ hasText: "Options & Greeks" }).click();
  await expect(page.locator(".page-title")).to_have_text("Options & Greeks");
  await page.goBack();
  await expect(page.locator(".page-title")).to_have_text("Bond Pricing");
  await page.goBack();
  await expect(page.locator(".page-title")).to_have_text("Market overview");
  await page.goForward();
  await expect(page.locator(".page-title")).to_have_text("Bond Pricing");
});

test("mobile navigation opens, selects a module and closes", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "Open navigation" }).click();
  await expect(page.locator(".sidebar.open")).to_be_visible();
  await page.locator(".sidebar.open .nav-item").filter({ hasText: "Treasury Bills" }).click();
  await expect(page.locator(".page-title")).to_have_text("Treasury Bills");
  await expect(page.locator(".sidebar.open")).to_have_count(0);
});

test("Treasury bill calculator and auction history respond to input", async ({ page }) => {
  await page.goto("/?module=Treasury%20Bills");
  await expect(page.locator(".page-title")).to_have_text("Treasury Bills");
  await expect(page.getByText("14 observations")).to_be_visible();
  await page.getByLabel("Face value (KES)").fill("50000");
  await page.getByLabel("Annual investment yield (%)").fill("9");
  await page.getByLabel("Days to maturity").fill("182");
  await expect(page.locator(".metric-card").filter({ hasText: "Estimated purchase price" })).to_be_visible();
  await expect(page.locator(".metric-card").filter({ hasText: "Estimated purchase price" })).not.to_contain_text("KES 0.00");
});

test("bond pricing recalculates and retains the full cash-flow schedule", async ({ page }) => {
  await page.goto("/?module=Bond%20Pricing");
  await page.getByLabel("Face value (KES)").fill("100000");
  await page.getByLabel("Annual coupon rate (%)").fill("12");
  await page.getByLabel("Yield to maturity (%)").fill("13");
  await page.getByLabel("Years to maturity").fill("5");
  await expect(page.getByText("Scheduled cash flows")).to_be_visible();
  await expect(page.locator(".metric-card").filter({ hasText: "Model clean price" })).to_be_visible();
  await expect(page.locator(".metric-card").filter({ hasText: "Model clean price" })).not.to_contain_text("KES 0.00");
});

test("options calculator switches call and put and returns the Greeks", async ({ page }) => {
  await page.goto("/?module=Options%20%26%20Greeks");
  await expect(page.getByText("Black–Scholes model")).to_be_visible();
  await expect(page.locator(".metric-card").filter({ hasText: "Call model value" })).to_be_visible();
  await page.locator(".panel select").selectOption("Put");
  await expect(page.locator(".metric-card").filter({ hasText: "Put model value" })).to_be_visible();
  await expect(page.getByText("Delta", { exact: true })).to_be_visible();
  await expect(page.getByText("Gamma", { exact: true })).to_be_visible();
});

test("risk, research and backtesting screens run their own calculations", async ({ page }) => {
  await page.goto("/?module=Risk%20Analysis");
  await expect(page.getByText("Historical VaR · 95%")).to_be_visible();
  await expect(page.getByText("Expected shortfall")).to_be_visible();

  await page.goto("/?module=Research%20Intelligence");
  await expect(page.getByText("Moving-average research")).to_be_visible();
  await page.getByLabel("Short window").fill("5");
  await page.getByLabel("Long window").fill("30");
  await expect(page.getByText("5-observation average")).to_be_visible();

  await page.goto("/?module=Backtesting");
  await expect(page.getByText("Moving-average strategy test")).to_be_visible();
  await page.getByLabel("Short average (observations)").fill("5");
  await page.getByLabel("Long average (observations)").fill("30");
  await page.getByLabel("Cost per position change (basis points)").fill("2");
  await expect(page.getByText("Strategy cumulative return")).to_be_visible();
  await expect(page.getByText("Buy-and-hold return")).to_be_visible();
});

test("portfolio weights validate to 100 percent and the basket view updates", async ({ page }) => {
  await page.goto("/?module=Portfolio");
  await expect(page.getByText("Currency exposure basket")).to_be_visible();
  await expect(page.getByText("Fully allocated")).to_be_visible();
  await page.getByLabel("USD/KES weight (%)").fill("50");
  await expect(page.getByText("Set weights to exactly 100%")).to_be_visible();
  await page.getByLabel("USD/KES weight (%)").fill("40");
  await expect(page.getByText("Weighted basket history")).to_be_visible();
});

test("historical explorer filters and exports the displayed data", async ({ page }) => {
  await page.goto("/?module=Historical%20Market%20Explorer");
  await expect(page.getByText("Historical observation explorer")).to_be_visible();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export CSV" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toContain("kfa-fx-observations.csv");
  await page.locator(".filter-grid select").nth(0).selectOption("Treasury bills");
  await page.locator(".filter-grid select").nth(2).selectOption("91");
  await expect(page.getByText("91", { exact: true }).first()).to_be_visible();
});

test("stress scenarios reject impossible values and recalculate valid shocks", async ({ page }) => {
  await page.goto("/?module=Stress%20Testing");
  await expect(page.getByText("Capital shock scenarios")).to_be_visible();
  await page.getByLabel("Selected FX shock (%)").fill("-100");
  await expect(page.getByText(/Use positive capital and bond value/)).to_be_visible();
  await page.getByLabel("Selected FX shock (%)").fill("-15");
  await expect(page.getByText("Stressed value")).to_be_visible();
});
