"use client";

import { useMemo, useState } from "react";
import { motion } from "motion/react";
import {
  Activity, ArrowDownRight, ArrowUpRight, BarChart3, BookOpen, BriefcaseBusiness,
  ChartNoAxesCombined, CircleDollarSign, FileText, Gauge, Globe2, Layers3,
  Search, ShieldCheck, TrendingUp, Wallet, Zap
} from "lucide-react";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, ComposedChart, Line, LineChart,
  ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis
} from "recharts";

export type FxRow = {date:string; instrument:string; value:number; source:string; source_url?:string|null};
export type BillRow = {date:string; tenor_days:number; rate:number; price?:number|null; issue_number?:string|null; source:string; source_url?:string|null};
export type MarketPayload = {
  ok:boolean; fx:FxRow[]; bills:BillRow[]; source:string; retrieved_at:string|null;
  health:{database?:string;database_connected?:boolean;fx_rows:number;bills_rows:number;latest_fx_observation?:string|null;latest_bill_observation?:string|null;last_refresh?:{status:string;completed_at:string|null;source:string;fx_rows_upserted:number;bill_rows_upserted:number}|null;warnings?:string[]};
};

export const MODULES = [
  {name:"Dashboard",group:"Overview",desc:"A current view of published market observations and system health.",icon:Gauge,color:"#087f8c"},
  {name:"Kenyan Market",group:"Markets",desc:"Follow one currency pair across its historical CBK observations.",icon:Globe2,color:"#087f8c"},
  {name:"Market Intelligence",group:"Markets",desc:"Compare currency direction, short-term moves and realised volatility.",icon:ChartNoAxesCombined,color:"#356bb3"},
  {name:"Yield Curve",group:"Fixed income",desc:"Read the latest available 91-, 182- and 364-day auction curve.",icon:TrendingUp,color:"#356bb3"},
  {name:"Treasury Bills",group:"Fixed income",desc:"Review auction history by tenor and calculate a purchase price.",icon:CircleDollarSign,color:"#d5a43b"},
  {name:"Bond Pricing",group:"Fixed income",desc:"Value coupon bonds and inspect duration and convexity.",icon:Layers3,color:"#356bb3"},
  {name:"Options & Greeks",group:"Quantitative tools",desc:"Price European options and measure their sensitivities.",icon:Zap,color:"#8064b2"},
  {name:"Backtesting",group:"Quantitative tools",desc:"Test a moving-average rule against historical FX observations.",icon:BarChart3,color:"#8064b2"},
  {name:"Risk Analysis",group:"Risk",desc:"Estimate historical FX VaR, expected shortfall and drawdown.",icon:Activity,color:"#c18a35"},
  {name:"Risk Intelligence",group:"Risk",desc:"Assess historical variation in Treasury bill auction yields.",icon:ShieldCheck,color:"#c18a35"},
  {name:"Stress Testing",group:"Risk",desc:"Apply explicit shocks to capital and modelled bond values.",icon:Activity,color:"#c45151"},
  {name:"Portfolio Intelligence",group:"Portfolio",desc:"Compare return and risk characteristics across FX series.",icon:BriefcaseBusiness,color:"#16835d"},
  {name:"Portfolio",group:"Portfolio",desc:"Build a weighted currency basket from aligned observations.",icon:Wallet,color:"#16835d"},
  {name:"Historical Market Explorer",group:"Research",desc:"Filter, inspect and export the underlying market observations.",icon:Search,color:"#64748b"},
  {name:"Research Intelligence",group:"Research",desc:"Study moving averages and trend relationships in one FX series.",icon:BookOpen,color:"#64748b"},
  {name:"Financial Reports",group:"Research",desc:"Compile a source-aware snapshot of the stored market history.",icon:FileText,color:"#64748b"}
] as const;

const PAIRS=["USD/KES","GBP/KES","EUR/KES"];
const TENORS=[91,182,364];
const money=(value:number,decimals=2)=>"KES "+new Intl.NumberFormat("en-KE",{minimumFractionDigits:decimals,maximumFractionDigits:decimals}).format(value);
const pct=(value:number,decimals=2)=>(value*100).toFixed(decimals)+"%";
const pp=(value:number,decimals=3)=>(value*100).toFixed(decimals)+" pp";
const mean=(values:number[])=>values.length?values.reduce((a,b)=>a+b,0)/values.length:0;
const stdev=(values:number[])=>values.length>1?Math.sqrt(values.reduce((sum,x)=>sum+Math.pow(x-mean(values),2),0)/(values.length-1)):0;
const returns=(values:number[])=>values.slice(1).map((v,i)=>values[i]===0?0:v/values[i]-1);
const maxDrawdown=(values:number[])=>{
  let peak=0, worst=0;
  for(const value of values){peak=Math.max(peak,value);if(peak>0)worst=Math.min(worst,value/peak-1);}
  return worst;
};
const quantile=(values:number[],q:number)=>{
  if(!values.length)return 0;
  const sorted=[...values].sort((a,b)=>a-b);
  return sorted[Math.max(0,Math.min(sorted.length-1,Math.ceil(q*sorted.length)-1))];
};
const csvDownload=(name:string,headers:string[],rows:(string|number)[][])=>{
  const escape=(value:string|number)=>'"'+String(value??"").replace(/"/g,'""')+'"';
  const body=[headers.map(escape).join(","),...rows.map(row=>row.map(escape).join(","))].join("\r\n");
  const blob=new Blob(["\uFEFF",body],{type:"text/csv;charset=utf-8"});
  const url=URL.createObjectURL(blob),link=document.createElement("a");
  link.href=url;link.download=name;link.click();URL.revokeObjectURL(url);
};
function Field({label,value,onChange,step="any",min,max}:{label:string;value:string;onChange:(value:string)=>void;step?:string;min?:string;max?:string}){
  return <label className="field"><span>{label}</span><input className="search" type="number" min={min} max={max} step={step} value={value} onChange={e=>onChange(e.target.value)}/></label>;
}
function Metric({label,value,note}:{label:string;value:string;note?:string}){
  return <motion.div className="metric-card" initial={false} animate={{opacity:1,y:0}} transition={{duration:.24}}>
    <div className="metric-label">{label}</div><div className="metric-value">{value}</div>{note&&<div className="metric-foot">{note}</div>}
  </motion.div>;
}
function Panel({title,note,children,action}:{title:string;note?:string;children:React.ReactNode;action?:React.ReactNode}){
  return <section className="panel"><div className="panel-head"><div><div className="panel-title">{title}</div>{note&&<div className="panel-note">{note}</div>}</div>{action}</div>{children}</section>;
}
function ChartFrame({children,height=280}:{children:React.ReactNode;height?:number}){
  return <div style={{width:"100%",height}}>{children}</div>;
}
function NoData({message}:{message:string}){
  return <div className="empty-state">{message}</div>;
}
function Table({headers,rows}:{headers:string[];rows:(string|number)[][]}){
  return <div style={{overflowX:"auto"}}><table className="data-table"><thead><tr>{headers.map(h=><th key={h}>{h}</th>)}</tr></thead><tbody>{rows.map((row,i)=><tr key={i}>{row.map((cell,j)=><td key={j}>{cell}</td>)}</tr>)}</tbody></table></div>;
}
function ChartTooltip(){return <Tooltip contentStyle={{borderRadius:9,border:"1px solid #e4eaf0",fontSize:11,boxShadow:"0 8px 24px rgba(20,43,67,.08)"}}/>;}
function pairRows(fx:FxRow[],pair:string){return fx.filter(row=>row.instrument===pair).sort((a,b)=>a.date.localeCompare(b.date));}
function seriesFor(fx:FxRow[],pair:string){
  const rows=pairRows(fx,pair),values=rows.map(x=>x.value),rets=returns(values);
  return {rows,values,rets};
}
function latestByPair(fx:FxRow[],pair:string){const rows=pairRows(fx,pair);return rows[rows.length-1]||null;}
function Dashboard({data,loading}:{data:MarketPayload|null;loading:boolean}){
  const fx=data?.fx||[],bills=data?.bills||[];
  const latestBills=useMemo(()=>{const d=bills.reduce((latest,row)=>!latest||row.date>latest?row.date:latest,"");return bills.filter(row=>row.date===d).sort((a,b)=>a.tenor_days-b.tenor_days);},[bills]);
  const chart=pairRows(fx,"USD/KES").slice(-50).map(x=>({date:x.date.slice(5),rate:x.value}));
  return <div className="workspace-stack">
    <div className="metric-grid">
      {PAIRS.map(pair=>{const row=latestByPair(fx,pair);return <Metric key={pair} label={pair} value={row?row.value.toFixed(4):"—"} note={row?"CBK observation · "+row.date:"No stored observation"}/>})}
      <Metric label="Database" value={data?.health.database_connected?"Connected":"Unavailable"} note={data?.health.database||"Waiting for response"}/>
    </div>
    <div className="dashboard-grid">
      <Panel title="USD / KES" note="Daily mean rate · 50 most recent observations">
        <ChartFrame><ResponsiveContainer><AreaChart data={chart}><defs><linearGradient id="usdFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#087f8c" stopOpacity={.18}/><stop offset="95%" stopColor="#087f8c" stopOpacity={0}/></linearGradient></defs><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7edf2"/><XAxis dataKey="date" tick={{fontSize:10,fill:"#8291a0"}} axisLine={false} tickLine={false}/><YAxis domain={["auto","auto"]} tick={{fontSize:10,fill:"#8291a0"}} axisLine={false} tickLine={false} width={48}/><ChartTooltip/><Area type="monotone" dataKey="rate" stroke="#087f8c" strokeWidth={2.2} fill="url(#usdFill)" activeDot={{r:4}}/></AreaChart></ResponsiveContainer></ChartFrame>
      </Panel>
      <Panel title="Treasury bill curve" note={latestBills[0]?.date||"No auction records"}>
        <div className="market-list">{TENORS.map(tenor=>{const row=latestBills.find(x=>x.tenor_days===tenor);return <div className="market-row" key={tenor}><div className="instrument">{tenor}-day<small>{row?.issue_number||"Latest recorded auction"}</small></div><div className="rate">{row?pct(row.rate,4):"—"}</div><div className="panel-note">{row?.date||"No record"}</div></div>})}</div>
        <div className="panel-note" style={{marginTop:12}}>Rates are stored as decimal yields and displayed as annual percentages.</div>
      </Panel>
    </div>
    <Panel title="Data coverage" note="Counts are read directly from the Neon market database">
      <div className="metric-grid"><Metric label="FX observations" value={(data?.health.fx_rows||0).toLocaleString("en-KE")} note={"Latest "+(data?.health.latest_fx_observation||"not available")}/><Metric label="Auction observations" value={(data?.health.bills_rows||0).toLocaleString("en-KE")} note={"Latest "+(data?.health.latest_bill_observation||"not available")}/><Metric label="Last successful import" value={data?.health.last_refresh?.completed_at?new Date(data.health.last_refresh.completed_at).toLocaleString("en-KE"):"Not yet recorded"} note={data?.health.last_refresh?.source||"Waiting for scheduled CBK refresh"}/></div>
      {loading&&<div className="panel-note">Checking the market data service…</div>}
    </Panel>
  </div>;
}

function KenyanMarket({data}:{data:MarketPayload}){
  const [pair,setPair]=useState<string>("USD/KES");
  const {rows,values,rets}=seriesFor(data.fx,pair);
  const change=values.length>1?values.at(-1)!/values.at(-2)!-1:0;
  const chart=rows.map(row=>({date:row.date,rate:row.value}));
  return <div className="workspace-stack">
    <Panel title="Exchange-rate history" note="Choose one pair to inspect its published CBK daily mean">
      <div className="control-row"><label className="field"><span>Currency pair</span><select className="search" value={pair} onChange={e=>setPair(e.target.value)}>{PAIRS.map(p=><option key={p}>{p}</option>)}</select></label><span className="panel-note">Source: Central Bank of Kenya</span></div>
      <div className="metric-grid"><Metric label="Latest rate" value={values.length?values.at(-1)!.toFixed(4):"—"} note={rows.at(-1)?.date||"No stored observation"}/><Metric label="Daily change" value={values.length>1?pct(change):"—"} note={change>0?"Shilling weakened against pair":change<0?"Shilling strengthened against pair":"No previous observation"}/><Metric label="Annualised volatility" value={rets.length?pct(stdev(rets)*Math.sqrt(252)):"—"} note="Sample standard deviation of daily returns"/><Metric label="Maximum drawdown" value={values.length?pct(maxDrawdown(values)):"—"} note="Peak-to-trough movement in the stored rate series"/></div>
      <ChartFrame height={320}><ResponsiveContainer><LineChart data={chart}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7edf2"/><XAxis dataKey="date" tick={{fontSize:10,fill:"#8291a0"}} minTickGap={30}/><YAxis domain={["auto","auto"]} tick={{fontSize:10,fill:"#8291a0"}} width={54}/><ChartTooltip/><Line type="monotone" dataKey="rate" name="KES per unit" stroke="#087f8c" strokeWidth={2} dot={false} activeDot={{r:4}}/></LineChart></ResponsiveContainer></ChartFrame>
    </Panel>
    <Panel title="Recent observations" note="Newest published values first">
      <Table headers={["Date","Pair","Rate","Publisher"]} rows={[...rows].slice(-30).reverse().map(row=>[row.date,row.instrument,row.value.toFixed(4),row.source])}/>
    </Panel>
  </div>;
}

function MarketIntelligence({data}:{data:MarketPayload}){
  const rows=PAIRS.map(pair=>{
    const {rows,values,rets}=seriesFor(data.fx,pair);
    const latest=values.at(-1),prior=values.at(-2),weekPrior=values.at(-6);
    const day=latest!==undefined&&prior?latest/prior-1:null;
    const week=latest!==undefined&&weekPrior?latest/weekPrior-1:null;
    const volatility=stdev(rets)*Math.sqrt(252);
    const signal=day===null?"Insufficient history":day>.005?"Shilling weaker":day<-.005?"Shilling firmer":"Little changed";
    return {pair,latest,day,week,volatility,signal,date:rows.at(-1)?.date||"—"};
  });
  const chart=rows.map(x=>({pair:x.pair,change:x.day===null?0:x.day*100,volatility:x.volatility*100}));
  return <div className="workspace-stack">
    <Panel title="Currency comparison" note="Signals describe the latest observed change, not a forecast">
      <Table headers={["Pair","Latest","Daily move","5-observation move","Annualised volatility","Reading"]} rows={rows.map(x=>[x.pair,x.latest?.toFixed(4)||"—",x.day===null?"—":pct(x.day,3),x.week===null?"—":pct(x.week,3),pct(x.volatility,2),x.signal])}/>
    </Panel>
    <div className="dashboard-grid">
      <Panel title="Daily percentage move" note="Comparable change across the three tracked currency pairs">
        <ChartFrame><ResponsiveContainer><BarChart data={chart}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7edf2"/><XAxis dataKey="pair" tick={{fontSize:10,fill:"#8291a0"}}/><YAxis tick={{fontSize:10,fill:"#8291a0"}} unit="%"/><ReferenceLine y={0} stroke="#9aa6b2"/><ChartTooltip/><Bar dataKey="change" name="Daily move" fill="#356bb3" radius={[4,4,0,0]}/></BarChart></ResponsiveContainer></ChartFrame>
      </Panel>
      <Panel title="Volatility comparison" note="Annualised standard deviation of observed daily returns">
        <ChartFrame><ResponsiveContainer><BarChart data={chart} layout="vertical"><CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e7edf2"/><XAxis type="number" tick={{fontSize:10,fill:"#8291a0"}} unit="%"/><YAxis dataKey="pair" type="category" tick={{fontSize:10,fill:"#8291a0"}} width={65}/><ChartTooltip/><Bar dataKey="volatility" name="Annualised volatility" fill="#087f8c" radius={[0,4,4,0]}/></BarChart></ResponsiveContainer></ChartFrame>
      </Panel>
    </div>
  </div>;
}

function YieldCurve({data}:{data:MarketPayload}){
  const dates=[...new Set(data.bills.map(row=>row.date))].sort();
  const latestDate=dates.at(-1)||"";
  const current=TENORS.map(tenor=>data.bills.filter(row=>row.tenor_days===tenor).sort((a,b)=>b.date.localeCompare(a.date))[0]).filter(Boolean) as BillRow[];
  const latestCurve=current.filter(row=>row.date===latestDate).sort((a,b)=>a.tenor_days-b.tenor_days);
  const curve=latestCurve.map(row=>({tenor:String(row.tenor_days),yield:row.rate*100}));
  const short=latestCurve.find(x=>x.tenor_days===91),long=latestCurve.find(x=>x.tenor_days===364);
  const spread=short&&long?long.rate-short.rate:null;
  const shape=spread===null?"Not enough matched tenors":spread>.0005?"Upward sloping":spread<-.0005?"Inverted":"Relatively flat";
  return <div className="workspace-stack">
    <Panel title="Latest recorded auction curve" note={latestDate||"No matched auction date"}>
      <div className="metric-grid">{TENORS.map(tenor=>{const row=latestCurve.find(x=>x.tenor_days===tenor);return <Metric key={tenor} label={tenor+"-day yield"} value={row?pct(row.rate,4):"—"} note={row?.issue_number||"No observation for this auction"}/>})}<Metric label="364s–91s spread" value={spread===null?"—":(spread*100).toFixed(3)+" pp"} note={shape}/></div>
      {curve.length>=2?<ChartFrame height={300}><ResponsiveContainer><LineChart data={curve}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7edf2"/><XAxis dataKey="tenor" tick={{fontSize:11,fill:"#8291a0"}} label={{value:"Tenor (days)",position:"insideBottom",offset:-3,fontSize:10}}/><YAxis tick={{fontSize:10,fill:"#8291a0"}} unit="%"/><ChartTooltip/><Line dataKey="yield" name="Auction yield" stroke="#356bb3" strokeWidth={2.5} dot={{r:5,fill:"#356bb3"}}/></LineChart></ResponsiveContainer></ChartFrame>:<NoData message="The latest auction does not contain two or more tenors on the same date. The interface will not interpolate missing auction yields."/>}
    </Panel>
    <Panel title="Curve history" note="Latest available observation for each tenor; individual auction dates are shown">
      <Table headers={["Tenor","Auction date","Market-weighted yield","Issue number","Source"]} rows={current.sort((a,b)=>a.tenor_days-b.tenor_days).map(row=>[row.tenor_days+" days",row.date,pct(row.rate,4),row.issue_number||"—",row.source])}/>
    </Panel>
  </div>;
}

function TreasuryBills({data}:{data:MarketPayload}){
  const [tenor,setTenor]=useState("91");
  const [face,setFace]=useState("100000");
  const [yieldRate,setYieldRate]=useState("8.75");
  const [days,setDays]=useState("91");
  const rows=data.bills.filter(row=>row.tenor_days===Number(tenor)).sort((a,b)=>a.date.localeCompare(b.date));
  const rates=rows.map(row=>row.rate);
  const price=Number(face)>0&&Number(days)>0?Number(face)/(1+(Number(yieldRate)/100)*Number(days)/365):0;
  const chart=rows.map(row=>({date:row.date,yield:row.rate*100}));
  return <div className="workspace-stack">
    <Panel title="Auction history by tenor" note="Choose one Treasury bill maturity; this is auction history, not an offer to invest">
      <div className="control-row"><label className="field"><span>Tenor</span><select className="search" value={tenor} onChange={e=>setTenor(e.target.value)}>{TENORS.map(t=><option key={t} value={t}>{t}-day Treasury bill</option>)}</select></label><Metric label="Latest market-weighted yield" value={rates.length?pct(rates.at(-1)!,4):"—"} note={rows.at(-1)?.date||"No auction record"}/><Metric label="Historical average" value={rates.length?pct(mean(rates),4):"—"} note={rows.length+" observations"}/><Metric label="Observed range" value={rates.length?((Math.max(...rates)-Math.min(...rates))*100).toFixed(3)+" pp":"—"} note="High less low in stored history"/></div>
      {chart.length>=2?<ChartFrame height={300}><ResponsiveContainer><LineChart data={chart}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7edf2"/><XAxis dataKey="date" minTickGap={25} tick={{fontSize:10,fill:"#8291a0"}}/><YAxis tick={{fontSize:10,fill:"#8291a0"}} unit="%"/><ChartTooltip/><Line dataKey="yield" name="Accepted rate" stroke="#d5a43b" strokeWidth={2.2} dot={false}/></LineChart></ResponsiveContainer></ChartFrame>:<NoData message="More than one auction observation is needed to draw a history for this tenor."/>}
      <Table headers={["Auction date","Accepted yield","Issue number","Source"]} rows={[...rows].reverse().map(row=>[row.date,pct(row.rate,4),row.issue_number||"—",row.source])}/>
    </Panel>
    <Panel title="Treasury bill purchase-price calculator" note="Investment-yield convention from the retained pricing engine; 365-day basis">
      <div className="metric-grid"><Field label="Face value (KES)" value={face} onChange={setFace} min="1"/><Field label="Annual investment yield (%)" value={yieldRate} onChange={setYieldRate} min="0"/><Field label="Days to maturity" value={days} onChange={setDays} min="1"/></div>
      <div className="metric-grid"><Metric label="Estimated purchase price" value={money(price)}/><Metric label="Discount to face" value={money(Number(face)-price)}/><Metric label="Holding-period return" value={price>0?pct((Number(face)-price)/price):"—"}/></div>
      <p className="panel-note">The auction yield field and the calculator input are separate. Confirm the accepted yield, settlement date, tax treatment and applicable CBK terms before making an investment decision.</p>
    </Panel>
  </div>;
}

function BondPricing(){
  const [face,setFace]=useState("100000"),[coupon,setCoupon]=useState("12"),[ytm,setYtm]=useState("13"),[years,setYears]=useState("5"),[frequency,setFrequency]=useState("2");
  const f=Number(face),c=Number(coupon)/100,y=Number(ytm)/100,n=Math.max(1,Number(frequency)),t=Number(years);
  const valid=f>0&&c>=0&&y>-1&&t>0&&t<=100&&[1,2,4].includes(n);
  const periods=Math.max(1,Math.round(t*n)),periodic=y/n,cashCoupon=f*c/n;
  const flows=Array.from({length:periods},(_,i)=>({period:i+1,time:(i+1)/n,cash:cashCoupon+(i===periods-1?f:0),pv:(cashCoupon+(i===periods-1?f:0))/Math.pow(1+periodic,i+1)}));
  const price=valid?flows.reduce((s,x)=>s+x.pv,0):0;
  const macaulay=price?flows.reduce((s,x)=>s+x.time*x.pv,0)/price:0;
  const modified=macaulay/(1+periodic);
  const convexity=price?flows.reduce((s,x)=>s+x.period*(x.period+1)*x.cash/(n*n*Math.pow(1+periodic,x.period+2)),0)/price:0;
  const bp=0.01,approxChange=-modified*bp+.5*convexity*bp*bp;
  return <div className="workspace-stack">
    <Panel title="Fixed-rate bond valuation" note="Periodic coupon discounting; default convention is semi-annual">
      <div className="metric-grid"><Field label="Face value (KES)" value={face} onChange={setFace} min="1"/><Field label="Annual coupon rate (%)" value={coupon} onChange={setCoupon} min="0"/><Field label="Yield to maturity (%)" value={ytm} onChange={setYtm}/><Field label="Years to maturity" value={years} onChange={setYears} min="0.01"/><label className="field"><span>Payments per year</span><select className="search" value={frequency} onChange={e=>setFrequency(e.target.value)}><option value="1">Annual</option><option value="2">Semi-annual</option><option value="4">Quarterly</option></select></label></div>
      {valid?<div className="metric-grid"><Metric label="Model clean price" value={money(price)} note={price>f?"Premium to par":price<f?"Discount to par":"At par"}/><Metric label="Macaulay duration" value={macaulay.toFixed(4)+" years"}/><Metric label="Modified duration" value={modified.toFixed(4)} note="Approximate percentage sensitivity per 1.00 yield change"/><Metric label="Convexity" value={convexity.toFixed(4)}/></div>:<NoData message="Enter a positive face value and maturity, a non-negative coupon, and a yield greater than −100%."/>}
      <div className="panel-note">A +1 basis-point yield move implies an approximate price change of {valid?pct(approxChange,4):"—"} using duration and convexity. This model does not include accrued interest, settlement date, day-count, call features or taxes.</div>
    </Panel>
    <Panel title="Scheduled cash flows" note="First 12 coupon periods; redemption is included in the final payment">
      {valid?<Table headers={["Period","Time (years)","Cash flow","Present value"]} rows={flows.slice(0,12).map(row=>[row.period,row.time.toFixed(2),money(row.cash),money(row.pv)])}/>:<NoData message="Valid bond inputs are required to calculate cash flows."/>}
    </Panel>
  </div>;
}

function normalPdf(x:number){return Math.exp(-.5*x*x)/Math.sqrt(2*Math.PI);}
function normalCdf(x:number){
  const sign=x<0?-1:1,z=Math.abs(x)/Math.sqrt(2),t=1/(1+.3275911*z);
  const erf=1-(((((1.061405429*t-1.453152027)*t)+1.421413741)*t-.284496736)*t+.254829592)*t*Math.exp(-z*z);
  return .5*(1+sign*erf);
}
function OptionsGreeks(){
  const [spot,setSpot]=useState("100"),[strike,setStrike]=useState("100"),[maturity,setMaturity]=useState("1"),[riskFree,setRiskFree]=useState("13"),[volatility,setVolatility]=useState("20"),[kind,setKind]=useState("Call");
  const S=Number(spot),K=Number(strike),T=Number(maturity),r=Number(riskFree)/100,sigma=Number(volatility)/100;
  const valid=S>0&&K>0&&T>0&&sigma>0&&r>-1;
  const d1=valid?(Math.log(S/K)+(r+sigma*sigma/2)*T)/(sigma*Math.sqrt(T)):0,d2=d1-sigma*Math.sqrt(Math.max(T,0));
  const disc=Math.exp(-r*T),pdf=normalPdf(d1);
  const price=valid?(kind==="Call"?S*normalCdf(d1)-K*disc*normalCdf(d2):K*disc*normalCdf(-d2)-S*normalCdf(-d1)):0;
  const delta=kind==="Call"?normalCdf(d1):normalCdf(d1)-1;
  const gamma=valid?pdf/(S*sigma*Math.sqrt(T)):0;
  const vega=valid?S*pdf*Math.sqrt(T)/100:0;
  const theta=valid?(kind==="Call"?(-S*pdf*sigma/(2*Math.sqrt(T))-r*K*disc*normalCdf(d2)):(-S*pdf*sigma/(2*Math.sqrt(T))+r*K*disc*normalCdf(-d2)))/365:0;
  const rho=valid?(kind==="Call"?K*T*disc*normalCdf(d2):-K*T*disc*normalCdf(-d2))/100:0;
  return <div className="workspace-stack">
    <Panel title="Black–Scholes model" note="European option; continuous risk-free rate, no dividends or transaction costs" action={<select className="search" value={kind} onChange={e=>setKind(e.target.value)}><option>Call</option><option>Put</option></select>}>
      <div className="metric-grid"><Field label="Underlying price" value={spot} onChange={setSpot} min="0.01"/><Field label="Strike price" value={strike} onChange={setStrike} min="0.01"/><Field label="Time to expiry (years)" value={maturity} onChange={setMaturity} min="0.001"/><Field label="Risk-free rate (%)" value={riskFree} onChange={setRiskFree}/><Field label="Volatility (%)" value={volatility} onChange={setVolatility} min="0.01"/></div>
      {valid?<div className="metric-grid"><Metric label={kind+" model value"} value={price.toFixed(6)}/><Metric label="Delta" value={delta.toFixed(5)}/><Metric label="Gamma" value={gamma.toFixed(6)}/><Metric label="Vega / 1 vol point" value={vega.toFixed(5)}/><Metric label="Theta / day" value={theta.toFixed(6)}/><Metric label="Rho / 1 rate point" value={rho.toFixed(5)}/></div>:<NoData message="Enter positive spot, strike, time to expiry and volatility. The risk-free rate must be greater than −100%."/>}
    </Panel>
    <Panel title="Model assumptions" note="Read before comparing model value with an observed market option price">
      <Table headers={["Input","Assumption"]} rows={[["Exercise","European, exercise only at expiry"],["Underlying","No dividends or carry adjustment"],["Volatility","Constant over the option life"],["Interest rate","Constant continuously compounded risk-free rate"],["Market frictions","No transaction costs, bid–ask spread or liquidity adjustment"]]}/>
    </Panel>
  </div>;
}

function RiskAnalysis({data}:{data:MarketPayload}){
  const [pair,setPair]=useState("USD/KES"),[capital,setCapital]=useState("1000000"),[confidence,setConfidence]=useState("95");
  const {rows,values,rets}=seriesFor(data.fx,pair),q=1-Number(confidence)/100,tail=quantile(rets,q);
  const varAmount=Math.max(0,-tail*Number(capital));
  const tailReturns=rets.filter(x=>x<=tail),es=Math.max(0,-mean(tailReturns)*Number(capital));
  const volatility=stdev(rets)*Math.sqrt(252);
  const bins=Array.from({length:12},(_,i)=>({label:(i-6).toString(),count:0}));
  const lower=Math.min(...rets),upper=Math.max(...rets),width=upper>lower?(upper-lower)/bins.length:1;
  for(const value of rets){const idx=Math.max(0,Math.min(bins.length-1,Math.floor((value-lower)/width)));bins[idx].count++;}
  return <div className="workspace-stack">
    <Panel title="Historical FX risk" note="Loss estimates are based on the selected pair's observed daily percentage changes">
      <div className="control-row"><label className="field"><span>Currency pair</span><select className="search" value={pair} onChange={e=>setPair(e.target.value)}>{PAIRS.map(x=><option key={x}>{x}</option>)}</select></label><Field label="Exposure value (KES)" value={capital} onChange={setCapital} min="1"/><label className="field"><span>Confidence level</span><select className="search" value={confidence} onChange={e=>setConfidence(e.target.value)}><option value="90">90%</option><option value="95">95%</option><option value="99">99%</option></select></label></div>
      <div className="metric-grid"><Metric label={"Historical VaR · "+confidence+"%"} value={rets.length?money(varAmount):"—"} note="Empirical lower-tail loss estimate"/><Metric label="Expected shortfall" value={rets.length?money(es):"—"} note="Average loss in the selected tail"/><Metric label="Annualised volatility" value={rets.length?pct(volatility):"—"} note="Sample daily return volatility × √252"/><Metric label="Maximum drawdown" value={values.length?pct(maxDrawdown(values)):"—"} note="Observed peak-to-trough decline"/></div>
    </Panel>
    <Panel title="Daily return distribution" note={"Observed returns for "+pair+"; the histogram is descriptive, not a probability forecast"}>
      {rets.length>=2?<ChartFrame height={280}><ResponsiveContainer><BarChart data={bins}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7edf2"/><XAxis dataKey="label" tick={{fontSize:10,fill:"#8291a0"}}/><YAxis tick={{fontSize:10,fill:"#8291a0"}}/><ChartTooltip/><Bar dataKey="count" name="Observations" fill="#c18a35" radius={[3,3,0,0]}/></BarChart></ResponsiveContainer></ChartFrame>:<NoData message="At least three valid prices are needed to estimate historical returns."/>}
      <p className="panel-note">VaR and expected shortfall use the empirical return sample. They do not guarantee a maximum loss; currency series are market proxies and not a diversified portfolio return history.</p>
    </Panel>
  </div>;
}

function RiskIntelligence({data}:{data:MarketPayload}){
  const [selected,setSelected]=useState<number[]>([91,182,364]);
  const summaries=selected.map(tenor=>{
    const rows=data.bills.filter(x=>x.tenor_days===tenor).sort((a,b)=>a.date.localeCompare(b.date));
    const values=rows.map(x=>x.rate),vol=stdev(values),avg=mean(values),relative=avg?vol/avg:0;
    const movement=values.length>1?values.at(-1)!-values[0]:0;
    const risk=relative>=.2?"Higher dispersion":relative>=.1?"Moderate dispersion":"Lower dispersion";
    return {tenor,rows,values,vol,avg,movement,risk,latest:values.at(-1)};
  });
  const toggle=(tenor:number)=>setSelected(items=>items.includes(tenor)?items.filter(x=>x!==tenor):[...items,tenor]);
  return <div className="workspace-stack">
    <Panel title="Treasury yield risk overview" note="This module measures variation in auction yields, not FX risk or portfolio VaR">
      <div className="control-row">{TENORS.map(tenor=><label key={tenor} className="check-option"><input type="checkbox" checked={selected.includes(tenor)} onChange={()=>toggle(tenor)}/>{tenor}-day</label>)}</div>
      <div className="metric-grid"><Metric label="Records selected" value={summaries.reduce((s,x)=>s+x.rows.length,0).toString()}/><Metric label="Tenors compared" value={summaries.length.toString()}/><Metric label="First auction date" value={data.bills.map(x=>x.date).sort()[0]||"—"}/><Metric label="Latest auction date" value={data.bills.map(x=>x.date).sort().at(-1)||"—"}/></div>
      {summaries.length?<Table headers={["Tenor","Latest yield","Average","High","Low","Std deviation","Total movement","Relative dispersion"]} rows={summaries.map(x=>[x.tenor+" days",x.latest===undefined?"—":pct(x.latest,4),pct(x.avg,4),x.values.length?pct(Math.max(...x.values),4):"—",x.values.length?pct(Math.min(...x.values),4):"—",pct(x.vol,4),pp(x.movement,4),x.risk])}/>:<NoData message="Select at least one tenor."/>}
    </Panel>
    {summaries.map(x=><Panel key={x.tenor} title={x.tenor+"-day interpretation"} note={x.rows.length+" auction observations"}>
      <p style={{fontSize:12,lineHeight:1.7,color:"var(--muted)",margin:0}}>The recorded yield has {x.movement>0.0005?"risen":x.movement<-.0005?"fallen":"remained broadly stable"} by {pp(x.movement,4)} between the first and latest available auction. Sample standard deviation is {pct(x.vol,4)}; dispersion relative to the average yield is {pct(x.avg?x.vol/x.avg:0,2)} ({x.risk.toLowerCase()}). These readings describe the stored sample and are not a rating of credit risk.</p>
    </Panel>)}
  </div>;
}

function HistoricalExplorer({data}:{data:MarketPayload}){
  const [kind,setKind]=useState("FX"),[pair,setPair]=useState("All"),[tenor,setTenor]=useState("All"),[from,setFrom]=useState(""),[to,setTo]=useState(""),[search,setSearch]=useState("");
  const fx=data.fx.filter(x=>(pair==="All"||x.instrument===pair)&&(!from||x.date>=from)&&(!to||x.date<=to)&&(!search||x.source.toLowerCase().includes(search.toLowerCase())||x.date.includes(search)));
  const bills=data.bills.filter(x=>(tenor==="All"||x.tenor_days===Number(tenor))&&(!from||x.date>=from)&&(!to||x.date<=to)&&(!search||x.source.toLowerCase().includes(search.toLowerCase())||x.date.includes(search)));
  const exportRows=kind==="FX"?fx.map(x=>[x.date,x.instrument,x.value,x.source]):bills.map(x=>[x.date,x.tenor_days,x.rate,x.issue_number||"",x.source]);
  const headers=kind==="FX"?["Date","Instrument","Rate","Source"]:["Auction date","Tenor days","Accepted rate","Issue number","Source"];
  return <div className="workspace-stack">
    <Panel title="Historical observation explorer" note="Filter the underlying records; export contains only the rows currently displayed">
      <div className="filter-grid"><label className="field"><span>Dataset</span><select className="search" value={kind} onChange={e=>setKind(e.target.value)}><option>FX</option><option>Treasury bills</option></select></label><label className="field"><span>Currency pair</span><select className="search" value={pair} onChange={e=>setPair(e.target.value)}><option>All</option>{PAIRS.map(x=><option key={x}>{x}</option>)}</select></label><label className="field"><span>Tenor</span><select className="search" value={tenor} onChange={e=>setTenor(e.target.value)}><option>All</option>{TENORS.map(x=><option key={x} value={x}>{x} days</option>)}</select></label><label className="field"><span>From</span><input className="search" type="date" value={from} onChange={e=>setFrom(e.target.value)}/></label><label className="field"><span>To</span><input className="search" type="date" value={to} onChange={e=>setTo(e.target.value)}/></label><label className="field"><span>Search source or date</span><input className="search" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Type to filter"/></label></div>
      <div className="panel-head"><span className="panel-note">{exportRows.length.toLocaleString("en-KE")} records match the filters</span><button className="primary-btn" onClick={()=>csvDownload(kind==="FX"?"kfa-fx-observations.csv":"kfa-treasury-bill-observations.csv",headers,exportRows)}>Export CSV</button></div>
      {kind==="FX"?<Table headers={headers} rows={[...exportRows].reverse().map(row=>[row[0],row[1],Number(row[2]).toFixed(4),row[3]])}/>:<Table headers={headers} rows={[...exportRows].reverse().map(row=>[row[0],row[1],pct(Number(row[2]),4),row[3],row[4]])}/>}
    </Panel>
  </div>;
}

function PortfolioIntelligence({data}:{data:MarketPayload}){
  const summaries=PAIRS.map(pair=>{
    const {rows,values,rets}=seriesFor(data.fx,pair);
    return {pair,rows,values,rets,total:values.length>1?values.at(-1)!/values[0]-1:0,vol:stdev(rets)*Math.sqrt(252),drawdown:maxDrawdown(values),avg:mean(rets)};
  });
  const returnsByDate=PAIRS.map(pair=>new Map(seriesFor(data.fx,pair).rows.slice(1).map((row,i)=>[row.date,seriesFor(data.fx,pair).values[i+1]/seriesFor(data.fx,pair).values[i]-1])));
  const correlations=PAIRS.map((a,i)=>PAIRS.map((b,j)=>{
    if(i===j)return "1.000";
    const common=[...returnsByDate[i].keys()].filter(date=>returnsByDate[j].has(date));
    const x=common.map(date=>returnsByDate[i].get(date)!),y=common.map(date=>returnsByDate[j].get(date)!);
    const mx=mean(x),my=mean(y),den=Math.sqrt(x.reduce((s,v)=>s+(v-mx)**2,0)*y.reduce((s,v)=>s+(v-my)**2,0));
    return den?((x.reduce((s,v,k)=>s+(v-mx)*(y[k]-my),0))/den).toFixed(3):"—";
  }));
  return <div className="workspace-stack">
    <Panel title="Relative performance" note="Each series is measured over its own available observation window">
      <Table headers={["Pair","Observations","First date","Latest date","Cumulative change","Annualised volatility","Max drawdown"]} rows={summaries.map(x=>[x.pair,x.rows.length,x.rows[0]?.date||"—",x.rows.at(-1)?.date||"—",pct(x.total),pct(x.vol),pct(x.drawdown)])}/>
    </Panel>
    <Panel title="Daily-return correlation" note="Pearson correlation over dates shared by each pair; FX crosses are not independent assets">
      <Table headers={["Pair",...PAIRS]} rows={PAIRS.map((pair,i)=>[pair,...correlations[i]])}/>
    </Panel>
    <Panel title="Risk and return profile" note="Historical cumulative change versus annualised realised volatility">
      <ChartFrame height={300}><ResponsiveContainer><ScatterChart><CartesianGrid strokeDasharray="3 3" stroke="#e7edf2"/><XAxis type="number" dataKey="vol" name="Annualised volatility" unit="%" tick={{fontSize:10,fill:"#8291a0"}}/><YAxis type="number" dataKey="return" name="Cumulative change" unit="%" tick={{fontSize:10,fill:"#8291a0"}}/><ChartTooltip/><Scatter data={summaries.map(x=>({pair:x.pair,vol:x.vol*100,return:x.total*100}))} fill="#087f8c"/></ScatterChart></ResponsiveContainer></ChartFrame>
    </Panel>
  </div>;
}

function Portfolio({data}:{data:MarketPayload}){
  const [amount,setAmount]=useState("1000000"),[weights,setWeights]=useState({"USD/KES":"40","GBP/KES":"30","EUR/KES":"30"});
  const weightSum=PAIRS.reduce((s,p)=>s+Number(weights[p as keyof typeof weights]||0),0);
  const perPair=PAIRS.map(pair=>({pair,weight:Number(weights[pair as keyof typeof weights]||0)}));
  const maps=PAIRS.map(pair=>{
    const rows=pairRows(data.fx,pair);
    return new Map(rows.slice(1).map((row,i)=>[row.date,rows[i].value?row.value/rows[i].value-1:0]));
  });
  const common=maps.length?[...maps[0].keys()].filter(date=>maps.every(map=>map.has(date))).sort():[];
  const daily=common.map(date=>perPair.reduce((s,item,i)=>s+(item.weight/100)*(maps[i].get(date)||0),0));
  const cumulative=daily.reduce((arr,r)=>{arr.push((arr.at(-1)||1)*(1+r));return arr;},[1] as number[]);
  const totalReturn=cumulative.length?cumulative.at(-1)!-1:0;
  const annualVol=stdev(daily)*Math.sqrt(252);
  const initial=Number(amount),ending=initial*(1+totalReturn);
  const valid=initial>0&&perPair.every(row=>row.weight>=0)&&Math.abs(weightSum-100)<.0001;
  return <div className="workspace-stack">
    <Panel title="Currency exposure basket" note="Illustrative weighted basket based on aligned CBK daily FX returns; it is not a brokerage portfolio">
      <div className="metric-grid"><Field label="Starting reference value (KES)" value={amount} onChange={setAmount} min="1"/>{perPair.map(row=><Field key={row.pair} label={row.pair+" weight (%)"} value={weights[row.pair as keyof typeof weights]} onChange={v=>setWeights(prev=>({...prev,[row.pair]:v}))} min="0" max="100"/>)}</div>
      <div className="panel-note">Total allocation: <strong>{weightSum.toFixed(2)}%</strong> {valid?"· Fully allocated":"· Set weights to exactly 100% before interpreting portfolio results."}</div>
      {valid?<div className="metric-grid"><Metric label="Starting value" value={money(initial)}/><Metric label="Historical reference value" value={money(ending)} note={pct(totalReturn)+" cumulative model change"}/><Metric label="Annualised volatility" value={pct(annualVol)}/><Metric label="Historical max drawdown" value={pct(maxDrawdown(cumulative))}/></div>:<NoData message="A positive starting value and weights totalling exactly 100% are required."/>}
      {valid&&<Table headers={["Currency pair","Weight","Contribution to model change"]} rows={perPair.map((row,i)=>{const ret=seriesFor(data.fx,row.pair).values;const assetReturn=ret.length>1?ret.at(-1)!/ret[0]-1:0;return [row.pair,pct(row.weight/100),pct(row.weight/100*assetReturn)]})}/>}
      <p className="panel-note">Returns are built from common observation dates. This simplified FX exposure model does not incorporate financing, bid–ask spreads, hedging, carry, taxes or position-specific trading costs.</p>
    </Panel>
    <Panel title="Weighted basket history" note="Growth of a notional 1.00 unit using the selected weights">
      {valid&&cumulative.length>2?<ChartFrame height={280}><ResponsiveContainer><AreaChart data={cumulative.map((value,i)=>({observation:i,value}))}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7edf2"/><XAxis dataKey="observation" tick={{fontSize:10,fill:"#8291a0"}}/><YAxis tick={{fontSize:10,fill:"#8291a0"}}/><ChartTooltip/><Area dataKey="value" name="Basket index" stroke="#16835d" fill="#16835d" fillOpacity={.12}/></AreaChart></ResponsiveContainer></ChartFrame>:<NoData message="There are not yet enough aligned daily observations for the selected currency basket."/>}
    </Panel>
  </div>;
}

function ResearchIntelligence({data}:{data:MarketPayload}){
  const [pair,setPair]=useState("USD/KES"),[short,setShort]=useState("20"),[long,setLong]=useState("60");
  const {rows,values}=seriesFor(data.fx,pair),s=Number(short),l=Number(long);
  const valid=Number.isInteger(s)&&Number.isInteger(l)&&s>=2&&l>s&&l<=values.length;
  const chart=rows.map((row,i)=>{
    const sma=(window:number)=>i+1>=window?mean(values.slice(i-window+1,i+1)):null;
    return {date:row.date,rate:row.value,short:sma(s),long:sma(l)};
  });
  const last=chart.at(-1),signal=last?.short!==null&&last?.short!==undefined&&last?.long!==null&&last?.long!==undefined?(last.short>last.long?"Short average above long average":"Short average below long average"):"Not enough observations";
  return <div className="workspace-stack">
    <Panel title="Moving-average research" note="Historical trend comparison; this module does not issue a trade instruction">
      <div className="control-row"><label className="field"><span>Currency pair</span><select className="search" value={pair} onChange={e=>setPair(e.target.value)}>{PAIRS.map(p=><option key={p}>{p}</option>)}</select></label><Field label="Short window" value={short} onChange={setShort} min="2" max="1000" step="1"/><Field label="Long window" value={long} onChange={setLong} min="3" max="1000" step="1"/></div>
      <div className="metric-grid"><Metric label="Latest observed rate" value={last?.rate.toFixed(4)||"—"}/><Metric label={s+"-observation average"} value={valid?last?.short?.toFixed(4)||"—":"—"}/><Metric label={l+"-observation average"} value={valid?last?.long?.toFixed(4)||"—":"—"}/><Metric label="Relationship" value={signal}/></div>
      {valid&&chart.length>=l?<ChartFrame height={340}><ResponsiveContainer><ComposedChart data={chart}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7edf2"/><XAxis dataKey="date" minTickGap={25} tick={{fontSize:10,fill:"#8291a0"}}/><YAxis domain={["auto","auto"]} tick={{fontSize:10,fill:"#8291a0"}}/><ChartTooltip/><Line dataKey="rate" name="Observed rate" stroke="#9aa6b2" strokeWidth={1.5} dot={false}/><Line dataKey="short" name={"SMA "+s} stroke="#087f8c" strokeWidth={2} dot={false}/><Line dataKey="long" name={"SMA "+l} stroke="#d5a43b" strokeWidth={2} dot={false}/></ComposedChart></ResponsiveContainer></ChartFrame>:<NoData message="Choose a short window below the long window. The selected pair also needs at least as many observations as the long window."/>}
    </Panel>
    <Panel title="Research notes" note="How to read this view">
      <p style={{fontSize:12,lineHeight:1.7,color:"var(--muted)",margin:0}}>A simple moving average gives equal weight to each observation in its window. The shorter average responds more quickly to recent changes, while the longer average is slower. A crossover is a historical description only; it can lag sudden market moves and can produce false signals in range-bound periods.</p>
    </Panel>
  </div>;
}

function FinancialReports({data}:{data:MarketPayload}){
  const generated=new Date().toLocaleString("en-KE");
  const fx=PAIRS.map(pair=>{const {rows,values,rets}=seriesFor(data.fx,pair);return {pair,rows,latest:values.at(-1),change:values.length>1?values.at(-1)!/values[0]-1:0,vol:stdev(rets)*Math.sqrt(252)};});
  const dates=data.bills.map(x=>x.date).sort(),latestDate=dates.at(-1)||"";
  const latestBills=TENORS.map(tenor=>data.bills.filter(x=>x.tenor_days===tenor).sort((a,b)=>b.date.localeCompare(a.date))[0]).filter(Boolean);
  const exportRows=[
    ...fx.map(x=>{const row=x.rows.at(-1);return ["FX",x.pair,row?.date||"",x.latest??"",pct(x.change),pct(x.vol),x.rows.length,row?.source||"",row?.source_url||""];}),
    ...latestBills.map(x=>["Treasury bill",x.tenor_days+" days",x.date,pct(x.rate,4),"","",data.bills.filter(row=>row.tenor_days===x.tenor_days).length,x.source,x.source_url||""])
  ];
  return <div className="workspace-stack">
    <Panel title="Market research report" note={"Generated "+generated+" · Source: Central Bank of Kenya"}>
      <div className="metric-grid"><Metric label="FX observations" value={data.fx.length.toLocaleString("en-KE")}/><Metric label="Auction observations" value={data.bills.length.toLocaleString("en-KE")}/><Metric label="FX coverage" value={(data.fx.map(x=>x.date).sort()[0]||"—")+" to "+(data.health.latest_fx_observation||"—")}/><Metric label="Auction coverage" value={(dates[0]||"—")+" to "+(data.health.latest_bill_observation||"—")}/></div>
      <div className="panel-head"><div><div className="panel-title">Currency market summary</div><div className="panel-note">Cumulative change over each series' available period</div></div><button className="primary-btn" onClick={()=>csvDownload("kenya-financial-analytics-report.csv",["Section","Instrument","Latest date","Latest value","Cumulative change","Annualised volatility","Observations"],exportRows)}>Download report CSV</button></div>
      <Table headers={["Pair","Latest date","Latest rate","Cumulative change","Annualised volatility","Observations","Source"]} rows={fx.map(x=>[x.pair,x.rows.at(-1)?.date||"—",x.latest?.toFixed(4)||"—",pct(x.change),pct(x.vol),x.rows.length,x.rows.at(-1)?.source||"—"])}/>
    </Panel>
    <Panel title="Latest Treasury bill auction snapshot" note={latestDate||"No auction results in database"}>
      <Table headers={["Tenor","Auction date","Accepted yield","Issue number","Source"]} rows={latestBills.map(row=>[row.tenor_days+" days",row.date,pct(row.rate,4),row.issue_number||"—",row.source])}/>
    </Panel>
    <Panel title="Source and limitations" note="Report provenance">
      <p style={{fontSize:12,lineHeight:1.7,color:"var(--muted)",margin:0}}>Market values in this report are stored observations attributed to the Central Bank of Kenya. Data coverage may differ by instrument. No rates are estimated for missing dates or tenors. Volatility is calculated from observed daily FX changes and is not a forward-looking risk forecast.</p>
    </Panel>
  </div>;
}

function Backtesting({data}:{data:MarketPayload}){
  const [pair,setPair]=useState("USD/KES"),[short,setShort]=useState("20"),[long,setLong]=useState("60"),[fee,setFee]=useState("0");
  const {rows,values}=seriesFor(data.fx,pair),s=Number(short),l=Number(long),cost=Number(fee)/10000;
  const valid=Number.isInteger(s)&&Number.isInteger(l)&&s>=2&&l>s&&Number.isFinite(cost)&&cost>=0&&values.length>l+1;
  const points=[];
  let equity=1,benchmark=1,position=0,trades=0,peak=1,worst=0;
  for(let i=1;valid&&i<values.length;i++){
    const ready=i>=l;
    const signal=ready&&mean(values.slice(i-s,i))>mean(values.slice(i-l,i))?1:0;
    const changed=signal!==position;
    if(changed){if(signal===1)trades++;position=signal;}
    const marketReturn=values[i-1]===0?0:values[i]/values[i-1]-1;
    const strategyReturn=position?marketReturn-(changed?cost:0):0;
    equity*=1+strategyReturn;benchmark*=1+marketReturn;peak=Math.max(peak,equity);worst=Math.min(worst,equity/peak-1);
    points.push({date:rows[i].date,strategy:equity,benchmark});
  }
  const strategyReturn=equity-1,benchmarkReturn=benchmark-1;
  return <div className="workspace-stack">
    <Panel title="Moving-average strategy test" note="Signals are formed from prior observations and applied to the next observed return">
      <div className="metric-grid"><label className="field"><span>Currency pair</span><select className="search" value={pair} onChange={e=>setPair(e.target.value)}>{PAIRS.map(x=><option key={x}>{x}</option>)}</select></label><Field label="Short average (observations)" value={short} onChange={setShort} min="2" max="1000" step="1"/><Field label="Long average (observations)" value={long} onChange={setLong} min="3" max="1000" step="1"/><Field label="Cost per position change (basis points)" value={fee} onChange={setFee} min="0" max="1000"/></div>
      {valid?<div className="metric-grid"><Metric label="Strategy cumulative return" value={pct(strategyReturn)} note="Long / cash rule, before tax"/><Metric label="Buy-and-hold return" value={pct(benchmarkReturn)}/><Metric label="Strategy max drawdown" value={pct(worst)}/><Metric label="Entries" value={trades.toString()} note="Position changes from cash to long"/></div>:<NoData message="The short window must be below the long window, and the selected FX pair must contain more observations than the long window."/>}
      {points.length?<ChartFrame height={320}><ResponsiveContainer><LineChart data={points}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7edf2"/><XAxis dataKey="date" minTickGap={25} tick={{fontSize:10,fill:"#8291a0"}}/><YAxis tick={{fontSize:10,fill:"#8291a0"}}/><ChartTooltip/><Line dataKey="strategy" name="Strategy index" stroke="#087f8c" strokeWidth={2} dot={false}/><Line dataKey="benchmark" name="Buy-and-hold index" stroke="#9aa6b2" strokeWidth={1.7} dot={false}/></LineChart></ResponsiveContainer></ChartFrame>:null}
    </Panel>
    <Panel title="Test design" note="Transparent assumptions">
      <Table headers={["Rule","Implementation"]} rows={[["Entry","Prior short-window average above prior long-window average"],["Position","Long when signal is positive; otherwise cash"],["Execution timing","Signal uses only observations available before the return being measured"],["Trading cost","User-specified basis points on each entry or exit"],["Excluded factors","Spread, slippage, funding, taxes, market impact and tradeable execution"]]} />
    </Panel>
  </div>;
}

function StressTesting(){
  const [capital,setCapital]=useState("1000000"),[fxShock,setFxShock]=useState("-10"),[face,setFace]=useState("1000000"),[duration,setDuration]=useState("4"),[convexity,setConvexity]=useState("22"),[bps,setBps]=useState("100");
  const value=Number(capital),shock=Number(fxShock)/100,faceValue=Number(face),mod=Number(duration),conv=Number(convexity),dy=Number(bps)/10000;
  const valid=value>0&&shock>-1&&shock<=5&&Number.isFinite(shock)&&faceValue>0&&mod>=0&&mod<=100&&conv>=0&&conv<=10000&&Math.abs(Number(bps))<=5000&&(-mod*dy+.5*conv*dy*dy)>-1;
  const stressedFx=value*(1+shock);
  const bondMove=-mod*dy+.5*conv*dy*dy,bondPrice=faceValue*(1+bondMove);
  const scenarios=[-30,-20,-15,-10,-5,0,5,10,15,20].map(x=>({shock:x,value:value*(1+x/100),pnl:value*x/100}));
  return <div className="workspace-stack">
    <Panel title="Capital shock scenarios" note="Deterministic scenarios applied to a user-entered reference portfolio value">
      <div className="metric-grid"><Field label="Reference value (KES)" value={capital} onChange={setCapital} min="1"/><Field label="Selected FX shock (%)" value={fxShock} onChange={setFxShock} min="-99" max="500"/></div>
      {valid?<><div className="metric-grid"><Metric label="Reference capital" value={money(value)}/><Metric label="FX shock P/L" value={money(stressedFx-value)}/><Metric label="Stressed value" value={money(stressedFx)}/><Metric label="Applied shock" value={pct(shock)}/></div><Table headers={["Scenario shock","Profit / loss","Stressed value"]} rows={scenarios.map(row=>[row.shock+"%",money(row.pnl),money(row.value)])}/></>:<NoData message="Use positive capital and bond value, an FX shock above −100%, non-negative duration and convexity, and a rate shock within ±5,000 basis points."/>}
    </Panel>
    <Panel title="Fixed-income rate shock" note="Duration-convexity approximation; yield shock is applied in basis points">
      <div className="metric-grid"><Field label="Bond reference value (KES)" value={face} onChange={setFace} min="1"/><Field label="Modified duration" value={duration} onChange={setDuration} min="0" max="100"/><Field label="Convexity" value={convexity} onChange={setConvexity} min="0" max="10000"/><Field label="Yield shock (basis points)" value={bps} onChange={setBps} min="-5000" max="5000"/></div>
      {valid?<div className="metric-grid"><Metric label="Estimated price change" value={pct(bondMove)}/><Metric label="Estimated stressed value" value={money(bondPrice)}/><Metric label="Estimated P/L" value={money(bondPrice-faceValue)}/></div>:<NoData message="Check the capital, duration, convexity and shock inputs. Inputs must be within the documented scenario bounds."/>}
      <p className="panel-note">This is a second-order approximation for a small parallel yield move. It is not a full revaluation of a particular bond or yield curve.</p>
    </Panel>
  </div>;
}

export function ModuleWorkspace({name,data,loading,error}:{name:string;data:MarketPayload|null;loading:boolean;error:string}){
  if(!data&&name!=="Dashboard")return <Panel title={name} note="Market service unavailable"><NoData message={error||"Waiting for the connected database."}/></Panel>;
  const payload=data||{ok:false,fx:[],bills:[],source:"Central Bank of Kenya",retrieved_at:null,health:{fx_rows:0,bills_rows:0}};
  switch(name){
    case "Dashboard":return <Dashboard data={data} loading={loading}/>;
    case "Kenyan Market":return <KenyanMarket data={payload}/>;
    case "Market Intelligence":return <MarketIntelligence data={payload}/>;
    case "Yield Curve":return <YieldCurve data={payload}/>;
    case "Treasury Bills":return <TreasuryBills data={payload}/>;
    case "Bond Pricing":return <BondPricing/>;
    case "Options & Greeks":return <OptionsGreeks/>;
    case "Risk Analysis":return <RiskAnalysis data={payload}/>;
    case "Risk Intelligence":return <RiskIntelligence data={payload}/>;
    case "Historical Market Explorer":return <HistoricalExplorer data={payload}/>;
    case "Portfolio Intelligence":return <PortfolioIntelligence data={payload}/>;
    case "Portfolio":return <Portfolio data={payload}/>;
    case "Research Intelligence":return <ResearchIntelligence data={payload}/>;
    case "Financial Reports":return <FinancialReports data={payload}/>;
    case "Backtesting":return <Backtesting data={payload}/>;
    case "Stress Testing":return <StressTesting/>;
    default:return <Panel title={name}><NoData message="This module is not available in this build."/></Panel>;
  }
}
