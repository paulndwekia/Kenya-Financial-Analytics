import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const workspaces = readFileSync(new URL("../app/components/workspaces.tsx", import.meta.url), "utf8");
const page = readFileSync(new URL("../app/page.tsx", import.meta.url), "utf8");

const start = workspaces.indexOf("export const MODULES = [");
const stop = workspaces.indexOf("] as const;", start);
assert.ok(start >= 0 && stop > start, "The module registry must be present.");
const registry = workspaces.slice(start, stop);
const names = [...registry.matchAll(/\{name:"([^"]+)"/g)].map(match => match[1]);
const dispatcher = workspaces.slice(workspaces.indexOf("export function ModuleWorkspace"));
const routes = [...dispatcher.matchAll(/case "([^"]+)":/g)].map(match => match[1]);

const functionName = {
  "Kenyan Market": "KenyanMarket",
  "Market Intelligence": "MarketIntelligence",
  "Yield Curve": "YieldCurve",
  "Treasury Bills": "TreasuryBills",
  "Bond Pricing": "BondPricing",
  "Options & Greeks": "OptionsGreeks",
  "Risk Analysis": "RiskAnalysis",
  "Risk Intelligence": "RiskIntelligence",
  "Historical Market Explorer": "HistoricalExplorer",
  "Portfolio Intelligence": "PortfolioIntelligence",
  "Portfolio": "Portfolio",
  "Research Intelligence": "ResearchIntelligence",
  "Financial Reports": "FinancialReports",
  "Backtesting": "Backtesting",
  "Stress Testing": "StressTesting",
  "Dashboard": "Dashboard"
};

function functionSource(name) {
  const startAt = workspaces.indexOf("function " + name + "(");
  assert.ok(startAt >= 0, "Missing workspace component: " + name);
  const candidates = [
    workspaces.indexOf("\nfunction ", startAt + 1),
    workspaces.indexOf("\nexport function ", startAt + 1)
  ].filter(index => index >= 0);
  return workspaces.slice(startAt, candidates.length ? Math.min(...candidates) : workspaces.length);
}

test("the 16 registered modules all have exactly one navigation dispatcher", () => {
  assert.equal(names.length, 16);
  assert.equal(new Set(names).size, names.length, "Module names must be unique.");
  assert.deepEqual([...routes].sort(), [...names].sort(), "Every sidebar workspace must resolve to a component.");
  assert.match(page, /MODULES\.filter\(item=>item\.group===group\)/);
  assert.match(page, /onClick=\{\(\)=>choose\(item\.name\)\}/);
  assert.match(page, /const choose=\(name:string\)=>\{/);
  assert.match(page, /setActive\(name\)/);
  assert.match(page, /setMenu\(false\)/);
});

test("every module exposes at least one real responsive chart", () => {
  for (const name of names) {
    const component = functionSource(functionName[name]);
    assert.match(component, /<ChartFrame/, name + " should render a chart frame.");
    assert.match(component, /<(Area|Bar|Line|Composed|Scatter)[A-Za-z]*Chart/, name + " should render a chart component.");
  }
});

test("chart views use separate modules for separate analytical tasks", () => {
  const bond = functionSource("BondPricing");
  const options = functionSource("OptionsGreeks");
  const risk = functionSource("RiskAnalysis");
  const explorer = functionSource("HistoricalExplorer");
  const stress = functionSource("StressTesting");
  assert.match(bond, /Bond price across yield scenarios/);
  assert.match(bond, /Annual coupon and principal profile/);
  assert.match(options, /Option value versus underlying price/);
  assert.match(options, /Delta and gamma by underlying price/);
  assert.match(risk, /Daily return distribution/);
  assert.match(explorer, /Exchange-rate history/);
  assert.match(explorer, /Observation records/);
  assert.match(explorer, /explorer-mobile-tabs/);
  assert.match(stress, /Combined CBK rate-shock impact/);
  assert.match(stress, /Portfolio-value shock curve/);
});
