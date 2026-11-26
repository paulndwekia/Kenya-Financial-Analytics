const DAY_COUNT=365;
const finite=(x,name)=>{const v=Number(x);if(!Number.isFinite(v))throw new TypeError(name+" must be finite.");return v;};
const positive=(x,name)=>{const v=finite(x,name);if(v<=0)throw new RangeError(name+" must be greater than zero.");return v;};
// All internal and public pricing functions accept rates as decimal fractions
// (0.09 means 9%). Percent-to-decimal conversion belongs in the UI input layer.
export const rateDecimal=x=>finite(x,"Rate");
const tenorDays=x=>{const n=Number(x);if(![91,182,364].includes(n))throw new RangeError("Kenyan Treasury Bill tenor must be 91, 182 or 364 days.");return n;};

export function treasuryBillPrice(faceValue,annualYield,days){
 const face=positive(faceValue,"Face value"),y=rateDecimal(annualYield),d=positive(days,"Days");
 if(1+y*d/DAY_COUNT<=0)throw new RangeError("Yield and tenor produce an invalid purchase price.");
 return face/(1+y*d/DAY_COUNT);
}
export function treasuryBillDiscountPrice(faceValue,discountRate,days){
 const face=positive(faceValue,"Face value"),r=rateDecimal(discountRate),d=positive(days,"Days");
 const price=face*(1-r*d/DAY_COUNT);if(price<=0)throw new RangeError("Discount rate produces a non-positive price.");return price;
}
export function treasuryBillYield(faceValue,price,days){
 const face=positive(faceValue,"Face value"),p=positive(price,"Price"),d=positive(days,"Days");
 if(p>=face)return 0;return (face/p-1)*DAY_COUNT/d;
}
export function treasuryBillDiscountRate(faceValue,price,days){
 const face=positive(faceValue,"Face value"),p=positive(price,"Price"),d=positive(days,"Days");
 return ((face-p)/face)*DAY_COUNT/d;
}
export function treasuryBillReturn(faceValue,annualYield,days){
 const price=treasuryBillPrice(faceValue,annualYield,days),face=positive(faceValue,"Face value"),d=positive(days,"Days");
 return {face_value:face,days:d,yield:rateDecimal(annualYield),purchase_price:price,profit:face-price,holding_period_return:face/price-1,annualized_return:(face/price-1)*DAY_COUNT/d};
}

export function bondCashFlows(faceValue,couponRate,years,frequency=2){
 const face=positive(faceValue,"Face value"),coupon=rateDecimal(couponRate),t=positive(years,"Years"),freq=positive(frequency,"Frequency");
 if(coupon<0)throw new RangeError("Coupon rate cannot be negative.");
 const exactPeriods=t*freq,periods=Math.round(exactPeriods);
 if(periods<1||periods>2000)throw new RangeError("Bond payment schedule is outside supported limits.");
 if(Math.abs(exactPeriods-periods)>1e-8)throw new RangeError("Maturity must be an exact multiple of the selected coupon period.");
 const amount=face*coupon/freq;
 return Array.from({length:periods},(_,i)=>({period:i+1,time:(i+1)/freq,cash_flow:amount+(i===periods-1?face:0)}));
}
export function bondPrice(faceValue,couponRate,yieldRate,years,frequency=2){
 const flows=bondCashFlows(faceValue,couponRate,years,frequency),y=rateDecimal(yieldRate),freq=positive(frequency,"Frequency");
 if(y<=-freq)throw new RangeError("Periodic yield must be greater than -100%.");
 return flows.reduce((sum,x)=>sum+x.cash_flow/Math.pow(1+y/freq,x.period),0);
}
export function bondYtm(faceValue,couponRate,marketPrice,years,frequency=2,tolerance=1e-10,maxIterations=200){
 const market=positive(marketPrice,"Market price");let low=-0.99,high=2;
 for(let i=0;i<maxIterations;i++){const mid=(low+high)/2,price=bondPrice(faceValue,couponRate,mid,years,frequency);const diff=price-market;if(Math.abs(diff)<tolerance)return mid;if(price>market)low=mid;else high=mid;}
 return (low+high)/2;
}
export function bondMetrics(faceValue,couponRate,yieldRate,years,frequency=2){
 const freq=positive(frequency,"Frequency"),y=rateDecimal(yieldRate),price=bondPrice(faceValue,couponRate,y,years,freq),flows=bondCashFlows(faceValue,couponRate,years,freq);
 const macaulay=flows.reduce((sum,x)=>sum+x.time*x.cash_flow/Math.pow(1+y/freq,x.period),0)/price;
 const modified=macaulay/(1+y/freq);
 const convexity=flows.reduce((sum,x)=>sum+x.period*(x.period+1)*x.cash_flow/Math.pow(1+y/freq,x.period+2),0)/(price*freq*freq);
 return {price,macaulay_duration:macaulay,modified_duration:modified,convexity};
}
export function bondPriceSensitivity(faceValue,couponRate,yieldRate,years,yieldChange,frequency=2){
 const metrics=bondMetrics(faceValue,couponRate,yieldRate,years,frequency),dy=finite(yieldChange,"Yield change");
 const pct=-metrics.modified_duration*dy+.5*metrics.convexity*dy*dy;
 return {current_price:metrics.price,estimated_price:metrics.price*(1+pct),estimated_change_percent:pct*100};
}

export function normalPdf(x){return Math.exp(-.5*x*x)/Math.sqrt(2*Math.PI);}
export function normalCdf(x){
 const sign=x<0?-1:1,z=Math.abs(x)/Math.sqrt(2),t=1/(1+.3275911*z);
 const erf=1-(((((1.061405429*t-1.453152027)*t)+1.421413741)*t-.284496736)*t+.254829592)*t*Math.exp(-z*z);
 return .5*(1+sign*erf);
}
export function blackScholes({spot,strike,time,rate,volatility,type="Call"}){
 const S=positive(spot,"Spot"),K=positive(strike,"Strike"),T=positive(time,"Time"),r=rateDecimal(rate),sigma=positive(volatility,"Volatility");
 if(r<=-1)throw new RangeError("Risk-free rate must be greater than -100%.");
 const d1=(Math.log(S/K)+(r+sigma*sigma/2)*T)/(sigma*Math.sqrt(T)),d2=d1-sigma*Math.sqrt(T),disc=Math.exp(-r*T),pdf=normalPdf(d1);
 const isCall=type.toLowerCase()==="call";
 const price=isCall?S*normalCdf(d1)-K*disc*normalCdf(d2):K*disc*normalCdf(-d2)-S*normalCdf(-d1);
 const delta=isCall?normalCdf(d1):normalCdf(d1)-1;
 return {price,delta,gamma:pdf/(S*sigma*Math.sqrt(T)),vega:S*pdf*Math.sqrt(T)/100,theta:(isCall?(-S*pdf*sigma/(2*Math.sqrt(T))-r*K*disc*normalCdf(d2)):(-S*pdf*sigma/(2*Math.sqrt(T))+r*K*disc*normalCdf(-d2)))/365,rho:(isCall?K*T*disc*normalCdf(d2):-K*T*disc*normalCdf(-d2))/100,d1,d2};
}

export function validateReturns(returns){const values=returns.map(x=>finite(x,"Return"));if(values.length<2)throw new RangeError("At least two return observations are required.");return values;}
export const average=values=>values.length?values.reduce((a,b)=>a+b,0)/values.length:0;
export const sampleStdDev=values=>values.length>1?Math.sqrt(values.reduce((s,x)=>s+Math.pow(x-average(values),2),0)/(values.length-1)):0;
export function historicalVaR(returns,portfolioValue,confidence=.95){
 const xs=validateReturns(returns).sort((a,b)=>a-b),v=positive(portfolioValue,"Portfolio value");
 if(!(confidence>0&&confidence<1))throw new RangeError("Confidence must be between 0 and 1.");
 const idx=Math.max(0,Math.min(Math.floor((1-confidence)*xs.length),xs.length-1));return Math.max(0,-xs[idx]*v);
}
export function parametricVaR(returns,portfolioValue,confidence=.95){
 const xs=validateReturns(returns),v=positive(portfolioValue,"Portfolio value");
 const z=confidence>=.99?2.32635:confidence>=.975?1.95996:confidence>=.95?1.64485:1.28155;
 return Math.max(0,(z*sampleStdDev(xs)-average(xs))*v);
}
export function expectedShortfall(returns,portfolioValue,confidence=.95){
 const xs=validateReturns(returns).sort((a,b)=>a-b),v=positive(portfolioValue,"Portfolio value");
 if(!(confidence>0&&confidence<1))throw new RangeError("Confidence must be between 0 and 1.");
 const cutoff=Math.max(1,Math.floor((1-confidence)*xs.length));return Math.max(0,-average(xs.slice(0,cutoff))*v);
}
export function annualizedVolatility(returns,annualization=252){return sampleStdDev(validateReturns(returns))*Math.sqrt(annualization);}
export function sharpeRatio(returns,riskFreeRate=0,annualization=252){
 const xs=validateReturns(returns),rf=finite(riskFreeRate,"Risk-free rate")/annualization,sd=sampleStdDev(xs);
 return sd===0?0:average(xs.map(x=>x-rf))/sd*Math.sqrt(annualization);
}
export function sortinoRatio(returns,targetReturn=0,annualization=252){
 const xs=validateReturns(returns),target=finite(targetReturn,"Target return");
 const downside=xs.map(x=>Math.min(x-target,0)),dd=Math.sqrt(average(downside.map(x=>x*x)));
 return dd===0?0:((average(xs)-target)*annualization)/(dd*Math.sqrt(annualization));
}
export function maximumDrawdown(returns,initialValue=1_000_000){
 const xs=validateReturns(returns);let value=positive(initialValue,"Initial value"),peak=value,worst=0;
 for(const r of xs){value*=1+r;if(value>peak)peak=value;const draw=(value-peak)/peak;if(draw<worst)worst=draw;}
 return {drawdown:worst,percentage:worst*100,ending_value:value,peak_value:peak};
}
export function levelDrawdown(levels){
 let peak=0,worst=0;for(const x of levels){peak=Math.max(peak,x);if(peak>0)worst=Math.min(worst,x/peak-1);}return worst;
}

export function classifyYieldCurve(rates){
 const values=[91,182,364].filter(t=>rates[t]!==undefined).map(t=>rates[t]);
 if(values.length<2)return "INSUFFICIENT DATA";
 if(values.every((x,i)=>i===0||values[i-1]<=x))return "UPWARD SLOPING";
 if(values.every((x,i)=>i===0||values[i-1]>=x))return "DOWNWARD SLOPING";
 return "MIXED / HUMPED";
}
export function yieldCurveSlopes(rates){
 const out={};for(const [name,a,b] of [["91_to_182",91,182],["182_to_364",182,364],["91_to_364",91,364]])if(rates[a]!==undefined&&rates[b]!==undefined)out[name]=rates[b]-rates[a];return out;
}
export function interpolateYield(maturityDays,rates){
 const target=positive(maturityDays,"Maturity");
 const pts=Object.entries(rates).map(([tenor,rate])=>[positive(tenor,"Observed tenor"),rateDecimal(rate)]).sort((a,b)=>a[0]-b[0]);
 if(!pts.length||target<pts[0][0]||target>pts.at(-1)[0])return null;
 if(target===pts[0][0])return pts[0][1];
 if(target===pts.at(-1)[0])return pts.at(-1)[1];
 for(let i=0;i<pts.length-1;i++){
  const [x1,y1]=pts[i],[x2,y2]=pts[i+1];
  if(x1<=target&&target<=x2)return y1+(target-x1)/(x2-x1)*(y2-y1);
 }
 return null;
}
export function simpleForwardRate(startSpotRate,endSpotRate,startDays,endDays){
 const r1=rateDecimal(startSpotRate),r2=rateDecimal(endSpotRate);
 const start=positive(startDays,"Forward start maturity"),end=positive(endDays,"Forward end maturity");
 if(end<=start)throw new RangeError("Forward end maturity must be greater than its start maturity.");
 const t1=start/DAY_COUNT,t2=end/DAY_COUNT;
 const startFactor=1+r1*t1,endFactor=1+r2*t2;
 if(startFactor<=0||endFactor<=0)throw new RangeError("Spot rates produce an invalid discount factor.");
 const startDiscount=1/startFactor,endDiscount=1/endFactor;
 return (startDiscount/endDiscount-1)/(t2-t1);
}

export function portfolioAllocation(assets){
 if(!assets.length)throw new RangeError("At least one portfolio asset is required.");
 const total=assets.reduce((s,a)=>s+positive(a.value,"Asset value"),0);
 if(total<=0)throw new RangeError("Portfolio value must be greater than zero.");
 return assets.map(a=>({name:a.name,value:Number(a.value),weight:Number(a.value)/total}));
}
export function portfolioMetrics(assets){
 const allocation=portfolioAllocation(assets),total=allocation.reduce((s,x)=>s+x.value,0);
 const expected=assets.reduce((s,a,i)=>s+allocation[i].weight*rateDecimal(a.expected_return),0);
 const variance=assets.reduce((s,a,i)=>s+allocation[i].weight**2*rateDecimal(a.volatility)**2,0);
 const hhi=allocation.reduce((s,x)=>s+x.weight*x.weight,0),largest=Math.max(...allocation.map(x=>x.weight));
 const vol=Math.sqrt(variance);
 return {total_value:total,expected_return:expected,expected_annual_pnl:total*expected,volatility:vol,concentration_hhi:hhi,largest_weight:largest,diversification_score:Math.max(0,Math.min(1,1-hhi)),parametric_var_95:1.64485*vol*total/Math.sqrt(252),allocation};
}
export function portfolioStress(assets,shock){
 const metrics=portfolioMetrics(assets),change=metrics.total_value*finite(shock,"Shock");return {portfolio_value:metrics.total_value,shock,change,ending_value:metrics.total_value+change};
}

export function applyShock(value,shock){const v=finite(value,"Value"),s=finite(shock,"Shock");return {starting_value:v,shock:s,change:v*s,ending_value:v*(1+s)};}
export function bondPriceShock(marketValue,modifiedDuration,convexity,yieldChange){
 const pct=-finite(modifiedDuration,"Duration")*finite(yieldChange,"Yield change")+.5*finite(convexity,"Convexity")*yieldChange**2;
 const change=finite(marketValue,"Market value")*pct;return {starting_value:marketValue,yield_change:yieldChange,percentage_change:pct,change,ending_value:marketValue+change};
}
export function treasuryBillReinvestmentShock(principal,currentRate,rateChange,tenor){
 const p=finite(principal,"Principal"),r=rateDecimal(currentRate),change=finite(rateChange,"Rate change"),days=tenorDays(tenor),newRate=r+change;
 const currentIncome=p*r*days/DAY_COUNT,stressedIncome=p*newRate*days/DAY_COUNT;
 return {principal:p,current_rate:r,stressed_rate:newRate,current_income:currentIncome,stressed_income:stressedIncome,income_change:stressedIncome-currentIncome};
}
export function curveScenario(rates,shortChange,longChange){
 const output={};for(const [tenor,rate] of Object.entries(rates)){const change=Number(tenor)<=182?shortChange:longChange;output[tenor]={current_rate:rate,stressed_rate:rate+change,change};}return output;
}
export function cbkRateScenarios(){return [{name:"CBK +50 bps",rate_change:.005},{name:"CBK +100 bps",rate_change:.01},{name:"CBK +200 bps",rate_change:.02},{name:"CBK -50 bps",rate_change:-.005},{name:"CBK -100 bps",rate_change:-.01}];}
