import test from "node:test";
import assert from "node:assert/strict";
import {
  treasuryBillPrice,treasuryBillDiscountPrice,treasuryBillYield,treasuryBillDiscountRate,
  bondPrice,bondYtm,bondMetrics,blackScholes,historicalVaR,parametricVaR,expectedShortfall,
  classifyYieldCurve,yieldCurveSlopes,interpolateYield,portfolioMetrics,bondPriceShock,
  treasuryBillReinvestmentShock,cbkRateScenarios
} from "../lib/finance.mjs";

test("Treasury bill investment-yield price uses a 365-day year",()=>{
  const p=treasuryBillPrice(100000,.09,91);
  assert.ok(Math.abs(p-97827.80)<.1);
});
test("Treasury bill discount and investment yield are distinct conventions",()=>{
  const investment=treasuryBillPrice(100000,.09,91);
  const discount=treasuryBillDiscountPrice(100000,.09,91);
  assert.notEqual(investment,discount);
  assert.ok(Math.abs(treasuryBillYield(100000,investment,91)-.09)<1e-10);
  assert.ok(Math.abs(treasuryBillDiscountRate(100000,discount,91)-.09)<1e-10);
});
test("Kenyan Treasury bill tenor validation rejects unsupported maturities",()=>{
  assert.throws(()=>treasuryBillReinvestmentShock(1e5,.09,.005,120),/tenor/i);
});
test("Bond price is at par when coupon and yield are equal",()=>{
  assert.ok(Math.abs(bondPrice(100000,.1,.1,5,2)-100000)<1e-7);
});
test("Bond yield solver recovers the input yield",()=>{
  const p=bondPrice(100000,.12,.135,7,2);
  assert.ok(Math.abs(bondYtm(100000,.12,p,7,2)-.135)<1e-8);
});
test("Bond duration and convexity are positive for a conventional bond",()=>{
  const m=bondMetrics(100000,.12,.13,5,2);
  assert.ok(m.macaulay_duration>0&&m.modified_duration>0&&m.convexity>0);
});
test("Black-Scholes call and put prices satisfy put-call parity",()=>{
  const c=blackScholes({spot:100,strike:100,time:1,rate:.1,volatility:.2,type:"Call"});
  const p=blackScholes({spot:100,strike:100,time:1,rate:.1,volatility:.2,type:"Put"});
  assert.ok(Math.abs((c.price-p.price)-(100-100*Math.exp(-.1)))<.02);
  assert.ok(c.gamma>0&&c.vega>0&&p.gamma>0&&p.vega>0);
});
test("Historical and parametric VaR and expected shortfall are non-negative",()=>{
  const r=[-.03,-.02,-.01,.002,.005,.01];
  assert.ok(historicalVaR(r,1e6,.95)>=0);
  assert.ok(parametricVaR(r,1e6,.95)>=0);
  assert.ok(expectedShortfall(r,1e6,.95)>=historicalVaR(r,1e6,.95));
});
test("Yield-curve shape, slopes and interpolation use only supplied points",()=>{
  const rates={91:.087,182:.088,364:.09};
  assert.equal(classifyYieldCurve(rates),"UPWARD SLOPING");
  assert.ok(Math.abs(yieldCurveSlopes(rates).91_to_182-.001)<1e-12);
  assert.ok(Math.abs(interpolateYield(136.5,rates)-.0875)<1e-12);
  assert.equal(classifyYieldCurve({91:.087}),"INSUFFICIENT DATA");
});
test("Portfolio measures calculate weighted return, concentration and diversification",()=>{
  const m=portfolioMetrics([
    {name:"A",value:600,expected_return:.1,volatility:.2},
    {name:"B",value:400,expected_return:.05,volatility:.1}
  ]);
  assert.equal(m.total_value,1000);
  assert.ok(Math.abs(m.expected_return-.08)<1e-12);
  assert.ok(m.concentration_hhi>0&&m.diversification_score>0);
});
test("CBK rate-shock scenario set has five named cases",()=>{
  const scenarios=cbkRateScenarios();
  assert.equal(scenarios.length,5);
  assert.equal(scenarios[0].name,"CBK +50 bps");
  const result=bondPriceShock(400000,4.5,25,.01);
  assert.ok(result.change<0);
  const t=treasuryBillReinvestmentShock(600000,.09,.01,91);
  assert.ok(t.income_change>0);
});
