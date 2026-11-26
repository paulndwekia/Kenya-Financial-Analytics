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
  const latestCurve=data.bills.filter(row=>row.date===latestDate).sort((a,b)=>a.tenor_days-b.tenor_days);
  const curve=latestCurve.map(row=>({tenor:String(row.tenor_days),yield:row.rate*100}));
  const short=latestCurve.find(x=>x.tenor_days===91),medium=latestCurve.find(x=>x.tenor_days===182),long=latestCurve.find(x=>x.tenor_days===364);
  const spread=short&&long?long.rate-short.rate:null;
  const ordered=[...latestCurve].sort((a,b)=>a.tenor_days-b.tenor_days);
  const allUp=ordered.length>=2&&ordered.every((row,i)=>i===0||row.rate>=ordered[i-1].rate);
  const allDown=ordered.length>=2&&ordered.every((row,i)=>i===0||row.rate<=ordered[i-1].rate);
  const shape=ordered.length<2?"Not enough matched tenors":allUp?"Upward / normal":allDown?"Downward / inverted":"Mixed / humped";
  const interpolate=(target:number):number|null=>{
    if(target<91||target>364||ordered.length<2)return null;
    for(let i=0;i<ordered.length-1;i++){
      const left=ordered[i],right=ordered[i+1];
      if(target>=left.tenor_days&&target<=right.tenor_days){
        const proportion=(target-left.tenor_days)/(right.tenor_days-left.tenor_days);
        return left.rate+proportion*(right.rate-left.rate);
      }
    }
    return target===ordered.at(-1)?.tenor_days?ordered.at(-1)!.rate:null;
  };
  const [startDays,setStartDays]=useState("91"),[endDays,setEndDays]=useState("364");
  const start=Number(startDays),end=Number(endDays),r1=interpolate(start),r2=interpolate(end);
  const t1=start/365,t2=end/365;
  const forwardRate=r1!==null&&r2!==null&&end>start
    ? Math.pow((Math.pow(1+r2,t2)/Math.pow(1+r1,t1)),1/(t2-t1))-1
    : null;
  const interpolationDays=[120,150,210,270,300];
  return <div className="workspace-stack">
    <Panel title="Latest recorded auction curve" note={latestDate||"No matched auction date"}>
      <div className="metric-grid">
        {TENORS.map(tenor=>{const row=latestCurve.find(x=>x.tenor_days===tenor);return <Metric key={tenor} label={tenor+"-day spot yield"} value={row?pct(row.rate,4):"—"} note={row?.issue_number||"No observation for this auction"}/>})}
        <Metric label="364s–91s spread" value={spread===null?"—":pp(spread,3)} note={shape}/>
      </div>
      {curve.length>=2?<ChartFrame height={300}><ResponsiveContainer><LineChart data={curve}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7edf2"/><XAxis dataKey="tenor" tick={{fontSize:11,fill:"#8291a0"}} label={{value:"Tenor (days)",position:"insideBottom",offset:-3,fontSize:10}}/><YAxis tick={{fontSize:10,fill:"#8291a0"}} unit="%"/><ChartTooltip/><Line dataKey="yield" name="Auction yield" stroke="#356bb3" strokeWidth={2.5} dot={{r:5,fill:"#356bb3"}}/></LineChart></ResponsiveContainer></ChartFrame>:<NoData message="The latest auction does not contain two or more tenors on the same date. No missing observations have been estimated."/>}
      <div className="panel-note">The curve uses only yields published for the same auction date. It does not combine the latest individual rates from different auctions.</div>
    </Panel>
    <Panel title="Interpolated spot rates" note="Linear interpolation between the latest matched 91-, 182- and 364-day observations">
      <Table headers={["Model maturity","Interpolated spot yield","Method"]} rows={interpolationDays.map(day=>{
        const value=interpolate(day);
        return [day+" days",value===null?"Not available":pct(value,4),"Linear between adjacent observed tenors"];
      })}/>
      <p className="panel-note">These intermediate maturities are model estimates, not separate CBK auction observations. Values are not extrapolated outside the published 91–364 day range.</p>
    </Panel>
    <Panel title="Implied forward rate" note="Annualised effective forward rate derived from interpolated spot rates">
      <div className="control-row">
        <label className="field"><span>Forward period starts (days)</span><select className="search" value={startDays} onChange={e=>setStartDays(e.target.value)}>{[91,120,150,182,210,270].map(x=><option key={x} value={x}>{x} days</option>)}</select></label>
        <label className="field"><span>Forward period ends (days)</span><select className="search" value={endDays} onChange={e=>setEndDays(e.target.value)}>{[182,210,270,300,364].map(x=><option key={x} value={x}>{x} days</option>)}</select></label>
      </div>
      <div className="metric-grid"><Metric label="Implied forward rate" value={forwardRate===null?"—":pct(forwardRate,4)} note={forwardRate===null?"Choose an increasing maturity pair with available spot rates":"From day "+start+" to day "+end}/><Metric label="Short spot rate" value={r1===null?"—":pct(r1,4)}/><Metric label="Long spot rate" value={r2===null?"—":pct(r2,4)}/></div>
    </Panel>
    <Panel title="Curve observations" note="Source records from the latest auction">
      <Table headers={["Tenor","Auction date","Market-weighted yield","Price per KES 100","Issue number","Source"]} rows={latestCurve.map(row=>[row.tenor_days+" days",row.date,pct(row.rate,4),row.price===null||row.price===undefined?"—":Number(row.price).toFixed(4),row.issue_number||"—",row.source])}/>
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
  const capital=Number(face),annualRate=Number(yieldRate)/100,term=Number(days);
  const valid=[capital,annualRate,term].every(Number.isFinite)&&capital>0&&annualRate>=0&&term>=1&&term<=364;
  const price=valid?capital/(1+annualRate*term/365):0;
  const discount=valid?capital-price:0;
  const investmentReturn=valid&&price>0?discount/price:0;
  const annualised=valid&&term>0?investmentReturn*365/term:0;
  const chart=rows.map(row=>({date:row.date,yield:row.rate*100}));
  const latestDate=data.bills.reduce((latest,row)=>!latest||row.date>latest?row.date:latest,"");
  const latestAuction=data.bills.filter(row=>row.date===latestDate).sort((a,b)=>a.tenor_days-b.tenor_days);
  const comparisons=TENORS.map(days=>{
    const row=latestAuction.find(item=>item.tenor_days===days);
    const purchase=row&&capital>0?capital/(1+row.rate*days/365):null;
    return {days,row,purchase,discount:purchase===null?null:capital-purchase};
  });
  return <div className="workspace-stack">
    <Panel title="Auction history by tenor" note="Choose one Treasury bill maturity; published auction observations only">
      <div className="control-row"><label className="field"><span>Tenor</span><select className="search" value={tenor} onChange={e=>setTenor(e.target.value)}>{TENORS.map(t=><option key={t} value={t}>{t}-day Treasury bill</option>)}</select></label><Metric label="Latest market-weighted yield" value={rates.length?pct(rates.at(-1)!,4):"—"} note={rows.at(-1)?.date||"No auction record"}/><Metric label="Historical average" value={rates.length?pct(mean(rates),4):"—"} note={rows.length+" observations"}/><Metric label="Observed range" value={rates.length?((Math.max(...rates)-Math.min(...rates))*100).toFixed(3)+" pp":"—"} note="High less low in stored history"/></div>
      {chart.length>=2?<ChartFrame height={300}><ResponsiveContainer><LineChart data={chart}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7edf2"/><XAxis dataKey="date" minTickGap={25} tick={{fontSize:10,fill:"#8291a0"}}/><YAxis tick={{fontSize:10,fill:"#8291a0"}} unit="%"/><ChartTooltip/><Line dataKey="yield" name="Market-weighted rate" stroke="#d5a43b" strokeWidth={2.2} dot={false}/></LineChart></ResponsiveContainer></ChartFrame>:<NoData message="More than one auction observation is needed to draw a history for this tenor."/>}
      <Table headers={["Auction date","Market-weighted yield","Issue number","Source"]} rows={[...rows].reverse().map(row=>[row.date,pct(row.rate,4),row.issue_number||"—",row.source])}/>
    </Panel>
    <Panel title="Treasury bill purchase-price calculator" note="Investment-yield convention from the retained pricing engine; 365-day basis">
      <div className="metric-grid"><Field label="Face value (KES)" value={face} onChange={setFace} min="1"/><Field label="Annual investment yield (%)" value={yieldRate} onChange={setYieldRate} min="0" max="100"/><Field label="Days to maturity" value={days} onChange={setDays} min="1" max="364"/></div>
      {valid?<div className="metric-grid"><Metric label="Estimated purchase price" value={money(price)}/><Metric label="Discount to face" value={money(discount)}/><Metric label="Holding-period return" value={pct(investmentReturn)}/><Metric label="Annualised return" value={pct(annualised)} note="Profit ÷ purchase price × 365 ÷ days"/></div>:<NoData message="Enter a positive face value, a non-negative annual yield and a remaining tenor from 1 to 364 days."/>}
      <p className="panel-note">The calculator uses the investment-yield convention documented in the original Treasury Bill engine. The auction history above reports CBK market-weighted rates; enter the relevant rate and remaining days for a specific purchase-price estimate.</p>
    </Panel>
    <Panel title="Same-auction tenor comparison" note={"Illustrative purchase prices using KES "+(Number.isFinite(capital)?capital.toLocaleString("en-KE"):"—")+" face value and the latest matched CBK auction on "+(latestDate||"no available date")}>
      <Table headers={["Tenor","Market-weighted yield","Estimated purchase price","Discount to face","Issue number"]} rows={comparisons.map(item=>[
        item.days+" days",item.row?pct(item.row.rate,4):"—",item.purchase===null?"—":money(item.purchase),item.discount===null?"—":money(item.discount),item.row?.issue_number||"—"
      ])}/>
      <p className="panel-note">This comparison uses actual rates recorded on one auction date. It does not imply that all three maturities are currently open for subscription.</p>
    </Panel>
  </div>;
}

function BondPricing(){
  const [face,setFace]=useState("100000"),[coupon,setCoupon]=useState("12"),[ytm,setYtm]=useState("13"),[years,setYears]=useState("5"),[frequency,setFrequency]=useState("2");
  const [marketPrice,setMarketPrice]=useState("95000"),[shockBps,setShockBps]=useState("100");
  const f=Number(face),c=Number(coupon)/100,y=Number(ytm)/100,n=Number(frequency),t=Number(years);
  const observedPrice=Number(marketPrice),dy=Number(shockBps)/10000;
  const valid=[f,c,y,n,t].every(Number.isFinite)&&f>0&&c>=0&&y>-1&&t>0&&t<=100&&[1,2,4].includes(n);
  const marketPriceValid=Number.isFinite(observedPrice)&&observedPrice>0;
  const shockValid=Number.isFinite(dy)&&Math.abs(Number(shockBps))<=5000;
  const periods=valid?Math.max(1,Math.round(t*n)):0,cashCoupon=f*c/n,periodic=y/n;
  const flows=Array.from({length:periods},(_,i)=>({period:i+1,time:(i+1)/n,cash:cashCoupon+(i===periods-1?f:0),pv:(cashCoupon+(i===periods-1?f:0))/Math.pow(1+periodic,i+1)}));
  const price=valid?flows.reduce((sum,row)=>sum+row.pv,0):0;
  const macaulay=price?flows.reduce((sum,row)=>sum+row.time*row.pv,0)/price:0;
  const modified=macaulay/(1+periodic);
  const convexity=price?flows.reduce((sum,row)=>sum+row.period*(row.period+1)*row.cash/(n*n*Math.pow(1+periodic,row.period+2)),0)/price:0;
  const priceAt=(yieldRate:number)=>{
    const rate=yieldRate/n;
    return Array.from({length:periods},(_,i)=>(cashCoupon+(i===periods-1?f:0))/Math.pow(1+rate,i+1)).reduce((sum,value)=>sum+value,0);
  };
  const minPrice=valid?priceAt(2.0):0,maxPrice=valid?priceAt(-.99):0;
  const ytmValid=valid&&marketPriceValid&&observedPrice>=minPrice&&observedPrice<=maxPrice;
  let low=-.99,high=2.0,impliedYtm:number|null=null;
  if(ytmValid){
    for(let i=0;i<120;i++){
      const mid=(low+high)/2;
      const estimate=priceAt(mid);
      if(Math.abs(estimate-observedPrice)<1e-8){low=mid;high=mid;break;}
      if(estimate>observedPrice)low=mid;else high=mid;
    }
    impliedYtm=(low+high)/2;
  }
  const estimatedChange=-modified*dy+.5*convexity*dy*dy;
  const shockedPrice=price*(1+estimatedChange);
  const sensitivityValid=valid&&shockValid&&Number.isFinite(shockedPrice)&&shockedPrice>0;
  return <div className="workspace-stack">
    <Panel title="Fixed-rate bond valuation" note="Periodic coupon discounting with the original annual, semi-annual and quarterly payment frequencies">
      <div className="metric-grid"><Field label="Face value (KES)" value={face} onChange={setFace} min="1"/><Field label="Annual coupon rate (%)" value={coupon} onChange={setCoupon} min="0" max="100"/><Field label="Yield to maturity (%)" value={ytm} onChange={setYtm} min="-99"/><Field label="Years to maturity" value={years} onChange={setYears} min="0.01" max="100"/><label className="field"><span>Payments per year</span><select className="search" value={frequency} onChange={e=>setFrequency(e.target.value)}><option value="1">Annual</option><option value="2">Semi-annual</option><option value="4">Quarterly</option></select></label></div>
      {valid?<div className="metric-grid"><Metric label="Model bond price" value={money(price)} note={price>f?"Premium to par":price<f?"Discount to par":"At par"}/><Metric label="Macaulay duration" value={macaulay.toFixed(4)+" years"}/><Metric label="Modified duration" value={modified.toFixed(4)}/><Metric label="Convexity" value={convexity.toFixed(4)}/></div>:<NoData message="Enter finite, valid face value, coupon, yield, maturity and payment frequency values."/>}
      <p className="panel-note">This is a periodic fixed-coupon model. Accrued interest, settlement date, day-count, embedded options, taxes and transaction costs are not included.</p>
    </Panel>
    <Panel title="Yield to maturity solver" note="Finds the annual yield that equates the model cash flows to an observed market price">
      <div className="metric-grid"><Field label="Observed market price (KES)" value={marketPrice} onChange={setMarketPrice} min="0.01"/></div>
      {ytmValid?<div className="metric-grid"><Metric label="Implied yield to maturity" value={pct(impliedYtm!,4)}/><Metric label="Re-priced value" value={money(priceAt(impliedYtm!))}/><Metric label="Market price entered" value={money(observedPrice)}/></div>:<NoData message={valid?"The entered market price is outside this solver's supported yield bracket (−99% to 200%).":"Enter valid bond terms before solving for yield."}/>}
    </Panel>
    <Panel title="Duration and convexity price sensitivity" note="Second-order approximation for a parallel yield shock">
      <div className="metric-grid"><Field label="Yield change (basis points)" value={shockBps} onChange={setShockBps} min="-5000" max="5000"/></div>
      {sensitivityValid?<div className="metric-grid"><Metric label="Estimated percentage change" value={pct(estimatedChange)}/><Metric label="Current model price" value={money(price)}/><Metric label="Estimated shocked price" value={money(shockedPrice)}/><Metric label="Estimated price change" value={money(shockedPrice-price)}/></div>:<NoData message="The selected shock produces an invalid estimated price. Check the yield and shock inputs."/>}
    </Panel>
    <Panel title="Scheduled coupon and redemption cash flows" note={periods+" payment periods · full schedule, not a sample"}>
      {valid?<Table headers={["Period","Time (years)","Coupon / redemption cash flow","Present value"]} rows={flows.map(row=>[row.period,row.time.toFixed(2),money(row.cash),money(row.pv)])}/>:<NoData message="Valid bond inputs are required to calculate the cash-flow schedule."/>}
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
  const valid=[S,K,T,sigma,r].every(Number.isFinite)&&S>0&&K>0&&T>0&&sigma>0&&r>-1;
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
  const lower=rets.length?Math.min(...rets):0,upper=rets.length?Math.max(...rets):0;
  const width=upper>lower?(upper-lower)/12:Math.max(Math.abs(lower)*0.1,0.000001);
  const bins=Array.from({length:12},(_,i)=>{
    const start=lower+i*width,end=i===11?upper:lower+(i+1)*width;
    return {label:(start*100).toFixed(2)+"% to "+(end*100).toFixed(2)+"%",count:0};
  });
  for(const value of rets){const idx=Math.max(0,Math.min(bins.length-1,Math.floor((value-lower)/width)));bins[idx].count++;}
  return <div className="workspace-stack">
    <Panel title="Historical FX risk" note="Loss estimates are based on the selected pair's observed daily percentage changes">
      <div className="control-row"><label className="field"><span>Currency pair</span><select className="search" value={pair} onChange={e=>setPair(e.target.value)}>{PAIRS.map(x=><option key={x}>{x}</option>)}</select></label><Field label="Exposure value (KES)" value={capital} onChange={setCapital} min="1"/><label className="field"><span>Confidence level</span><select className="search" value={confidence} onChange={e=>setConfidence(e.target.value)}><option value="90">90%</option><option value="95">95%</option><option value="99">99%</option></select></label></div>
      <div className="metric-grid"><Metric label={"Historical VaR · "+confidence+"%"} value={rets.length?money(varAmount):"—"} note="Empirical lower-tail loss estimate"/><Metric label="Expected shortfall" value={rets.length?money(es):"—"} note="Average loss in the selected tail"/><Metric label="Annualised volatility" value={rets.length?pct(volatility):"—"} note="Sample daily return volatility × √252"/><Metric label="Maximum drawdown" value={values.length?pct(maxDrawdown(values)):"—"} note="Observed peak-to-trough decline"/></div>
    </Panel>
    <Panel title="Daily return distribution" note={"Observed returns for "+pair+"; labels show actual sample-return intervals"}>
      {rets.length>=2?<ChartFrame height={280}><ResponsiveContainer><BarChart data={bins}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7edf2"/><XAxis dataKey="label" tick={{fontSize:10,fill:"#8291a0"}}/><YAxis tick={{fontSize:10,fill:"#8291a0"}}/><ChartTooltip/><Bar dataKey="count" name="Observations" fill="#c18a35" radius={[3,3,0,0]}/></BarChart></ResponsiveContainer></ChartFrame>:<NoData message="At least three valid prices are needed to estimate historical returns."/>}
      <p className="panel-note">VaR and expected shortfall use the empirical return sample. They do not guarantee a maximum loss; currency series are market proxies and not a diversified portfolio return history.</p>
    </Panel>
  </div>;
}

function RiskIntelligence({data}:{data:MarketPayload}){
  const summaries=PAIRS.map(pair=>{
    const {rows,values,rets}=seriesFor(data.fx,pair);
    const latest=values.at(-1),previous=values.at(-2);
    const daily=latest!==undefined&&previous!==undefined&&previous!==0?latest/previous-1:null;
    return {
      pair,
      rows,
      latest,
      daily,
      volatility:stdev(rets)*Math.sqrt(252),
      drawdown:maxDrawdown(values),
      observations:rets.length,
      latestDate:rows.at(-1)?.date||"—",
    };
  }).filter(x=>x.observations>0);
  const highestVol=summaries.reduce((best,row)=>!best||row.volatility>best.volatility?row:best,null as typeof summaries[number]|null);
  const deepestDrawdown=summaries.reduce((best,row)=>!best||row.drawdown<best.drawdown?row:best,null as typeof summaries[number]|null);
  const chart=summaries.map(row=>({pair:row.pair,volatility:row.volatility*100,drawdown:Math.abs(row.drawdown)*100}));
  return <div className="workspace-stack">
    <Panel title="FX risk comparison" note="Annualised realised volatility and peak-to-trough movement across the CBK currency series">
      <div className="metric-grid">
        <Metric label="Pairs with usable history" value={String(summaries.length)} note="USD, GBP and EUR against KES"/>
        <Metric label="Highest realised volatility" value={highestVol?highestVol.pair:"—"} note={highestVol?pct(highestVol.volatility):"Insufficient history"}/>
        <Metric label="Largest observed drawdown" value={deepestDrawdown?deepestDrawdown.pair:"—"} note={deepestDrawdown?pct(deepestDrawdown.drawdown):"Insufficient history"}/>
        <Metric label="Latest FX observation" value={summaries.map(row=>row.latestDate).sort().at(-1)||"—"} note="Date supplied by CBK"/>
      </div>
      <Table headers={["Pair","Observations","Latest rate","Daily move","Annualised volatility","Maximum drawdown","Latest date"]} rows={summaries.map(row=>[
        row.pair,row.observations,row.latest?.toFixed(4)||"—",row.daily===null?"—":pct(row.daily,3),pct(row.volatility,2),pct(row.drawdown),row.latestDate
      ])}/>
    </Panel>
    <div className="dashboard-grid">
      <Panel title="Realised volatility ranking" note="Sample standard deviation of daily returns multiplied by √252">
        <ChartFrame height={260}><ResponsiveContainer><BarChart data={chart} layout="vertical"><CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e7edf2"/><XAxis type="number" tick={{fontSize:10,fill:"#8291a0"}} unit="%"/><YAxis dataKey="pair" type="category" tick={{fontSize:10,fill:"#8291a0"}} width={65}/><ChartTooltip/><Bar dataKey="volatility" name="Annualised volatility" fill="#c18a35" radius={[0,4,4,0]}/></BarChart></ResponsiveContainer></ChartFrame>
      </Panel>
      <Panel title="Peak-to-trough comparison" note="Maximum historical drawdown in the stored KES-per-currency rate series">
        <ChartFrame height={260}><ResponsiveContainer><BarChart data={chart}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7edf2"/><XAxis dataKey="pair" tick={{fontSize:10,fill:"#8291a0"}}/><YAxis tick={{fontSize:10,fill:"#8291a0"}} unit="%"/><ChartTooltip/><Bar dataKey="drawdown" name="Drawdown magnitude" fill="#356bb3" radius={[4,4,0,0]}/></BarChart></ResponsiveContainer></ChartFrame>
      </Panel>
    </div>
    <Panel title="How to read this monitor" note="Risk indicators are historical descriptions">
      <p style={{fontSize:12,lineHeight:1.7,color:"var(--muted)",margin:0}}>The pair with the highest observed volatility had the widest variation in daily percentage changes over its available sample. Maximum drawdown measures the largest decline from a previous peak in the quoted KES-per-currency rate. These measures do not capture position size, leverage, hedging, transaction costs or future market conditions. Use the selected-pair VaR analysis in Risk Analysis for an exposure-specific loss estimate.</p>
    </Panel>
  </div>;
}

function HistoricalExplorer({data}:{data:MarketPayload}){
  const [kind,setKind]=useState("FX"),[pair,setPair]=useState("All"),[tenor,setTenor]=useState("All"),[from,setFrom]=useState(""),[to,setTo]=useState(""),[search,setSearch]=useState("");
  const fx=data.fx.filter(x=>(pair==="All"||x.instrument===pair)&&(!from||x.date>=from)&&(!to||x.date<=to)&&(!search||x.source.toLowerCase().includes(search.toLowerCase())||x.date.includes(search)));
  const bills=data.bills.filter(x=>(tenor==="All"||x.tenor_days===Number(tenor))&&(!from||x.date>=from)&&(!to||x.date<=to)&&(!search||x.source.toLowerCase().includes(search.toLowerCase())||x.date.includes(search)));
  const exportRows=kind==="FX"?fx.map(x=>[x.date,x.instrument,x.value,x.source]):bills.map(x=>[x.date,x.tenor_days,x.rate,x.issue_number||"",x.source]);
  const headers=kind==="FX"?["Date","Instrument","Rate","Source"]:["Auction date","Tenor days","Market-weighted rate","Issue number","Source"];
  return <div className="workspace-stack">
    <Panel title="Historical observation explorer" note="Filter the underlying records; export contains only the rows currently displayed">
      <div className="filter-grid">
        <label className="field"><span>Dataset</span><select className="search" value={kind} onChange={e=>setKind(e.target.value)}><option>FX</option><option>Treasury bills</option></select></label>
        {kind==="FX"
          ? <label className="field"><span>Currency pair</span><select className="search" value={pair} onChange={e=>setPair(e.target.value)}><option>All</option>{PAIRS.map(x=><option key={x}>{x}</option>)}</select></label>
          : <label className="field"><span>Tenor</span><select className="search" value={tenor} onChange={e=>setTenor(e.target.value)}><option>All</option>{TENORS.map(x=><option key={x} value={x}>{x} days</option>)}</select></label>}
        <label className="field"><span>From</span><input className="search" type="date" value={from} onChange={e=>setFrom(e.target.value)}/></label>
        <label className="field"><span>To</span><input className="search" type="date" value={to} onChange={e=>setTo(e.target.value)}/></label>
        <label className="field"><span>Search source or date</span><input className="search" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Type to filter"/></label>
      </div>
      <div className="panel-head"><span className="panel-note">{exportRows.length.toLocaleString("en-KE")} records match the filters</span><button className="primary-btn" onClick={()=>csvDownload(kind==="FX"?"kfa-fx-observations.csv":"kfa-treasury-bill-observations.csv",headers,exportRows)}>Export CSV</button></div>
      {kind==="FX"?<Table headers={headers} rows={[...exportRows].reverse().map(row=>[row[0],row[1],Number(row[2]).toFixed(4),row[3]])}/>:<Table headers={headers} rows={[...exportRows].reverse().map(row=>[row[0],row[1],pct(Number(row[2]),4),row[3],row[4]])}/>}
    </Panel>
  </div>;
}

function PortfolioIntelligence({data}:{data:MarketPayload}){
  const [values,setValues]=useState({t91:"300000",t182:"300000",t364:"250000",bond:"150000",cash:"0"});
  const [bondReturn,setBondReturn]=useState("10"),[bondVol,setBondVol]=useState("8");
  const [cashReturn,setCashReturn]=useState("3"),[cashVol,setCashVol]=useState("0.5");
  const updateValue=(key:keyof typeof values,value:string)=>setValues(previous=>({...previous,[key]:value}));
  const latestRate=(tenor:number)=>{
    const rows=data.bills.filter(row=>row.tenor_days===tenor).sort((x,y)=>x.date.localeCompare(y.date));
    return rows.at(-1)||null;
  };
  const historicalYieldChangeVol=(tenor:number)=>{
    const rows=data.bills.filter(row=>row.tenor_days===tenor).sort((x,y)=>x.date.localeCompare(y.date));
    const changes=rows.slice(1).map((row,i)=>row.rate-rows[i].rate);
    return stdev(changes);
  };
  const historicalBillPriceVol=(tenor:number)=>{
    const rows=data.bills.filter(row=>row.tenor_days===tenor).sort((x,y)=>x.date.localeCompare(y.date));
    const priceMoves=rows.slice(1).map((row,i)=>{
      const previous=rows[i];
      const duration=(tenor/365)/(1+previous.rate*tenor/365);
      return -duration*(row.rate-previous.rate);
    });
    const intervals=rows.slice(1).map((row,i)=>(new Date(row.date).getTime()-new Date(rows[i].date).getTime())/86400000).filter(days=>days>0);
    const averageInterval=mean(intervals);
    return averageInterval>0?stdev(priceMoves)*Math.sqrt(365/averageInterval):0;
  };
  const positions=[
    {id:"t91" as const,name:"91-Day Treasury Bill",value:Number(values.t91),latest:latestRate(91),expected:latestRate(91)?.rate??0,volatility:historicalBillPriceVol(91),isTbill:true,tenor:91},
    {id:"t182" as const,name:"182-Day Treasury Bill",value:Number(values.t182),latest:latestRate(182),expected:latestRate(182)?.rate??0,volatility:historicalBillPriceVol(182),isTbill:true,tenor:182},
    {id:"t364" as const,name:"364-Day Treasury Bill",value:Number(values.t364),latest:latestRate(364),expected:latestRate(364)?.rate??0,volatility:historicalBillPriceVol(364),isTbill:true,tenor:364},
    {id:"bond" as const,name:"Government Bond",value:Number(values.bond),latest:null,expected:Number(bondReturn)/100,volatility:Number(bondVol)/100,isTbill:false,tenor:0},
    {id:"cash" as const,name:"Cash",value:Number(values.cash),latest:null,expected:Number(cashReturn)/100,volatility:Number(cashVol)/100,isTbill:false,tenor:0},
  ];
  const valid=positions.every(row=>Number.isFinite(row.value)&&row.value>=0&&Number.isFinite(row.expected)&&Number.isFinite(row.volatility)&&row.volatility>=0)&&Number.isFinite(Number(bondReturn))&&Number.isFinite(Number(bondVol))&&Number.isFinite(Number(cashReturn))&&Number.isFinite(Number(cashVol));
  const active=positions.filter(row=>row.value>0);
  const total=active.reduce((sum,row)=>sum+row.value,0);
  const alloc=active.map(row=>({...row,weight:total?row.value/total:0,annualPnl:row.value*row.expected}));
  const expectedPnl=alloc.reduce((sum,row)=>sum+row.annualPnl,0);
  const expectedReturn=total?expectedPnl/total:0;
  const variance=alloc.reduce((sum,row)=>sum+row.weight**2*row.volatility**2,0);
  const portfolioVolatility=Math.sqrt(variance);
  const var95=1.64485*portfolioVolatility*total/Math.sqrt(252);
  const var99=2.32635*portfolioVolatility*total/Math.sqrt(252);
  const largest=alloc.reduce((best,row)=>!best||row.weight>best.weight?row:best,null as typeof alloc[number]|null);
  const hhi=alloc.reduce((sum,row)=>sum+row.weight**2,0);
  const diversification=Math.max(0,Math.min(1,1-hhi));
  const tbillValue=alloc.filter(row=>row.isTbill).reduce((sum,row)=>sum+row.value,0);
  const tbillWeight=total?tbillValue/total:0;
  const chart=alloc.map(row=>({asset:row.name,value:row.weight*100}));
  const riskRows=alloc.filter(row=>row.isTbill).map(row=>({
    name:row.name,weight:row.weight,yield:row.latest?.rate??null,volatility:historicalYieldChangeVol(row.tenor),priceVolatility:row.volatility,contribution:row.weight*row.volatility
  }));
  return <div className="workspace-stack">
    <Panel title="Fixed-income portfolio construction" note="Enter KES position values; Treasury bill expected yields link to the latest stored CBK auction result">
      <div className="metric-grid">
        <Field label="91-day Treasury bill value (KES)" value={values.t91} onChange={v=>updateValue("t91",v)} min="0"/>
        <Field label="182-day Treasury bill value (KES)" value={values.t182} onChange={v=>updateValue("t182",v)} min="0"/>
        <Field label="364-day Treasury bill value (KES)" value={values.t364} onChange={v=>updateValue("t364",v)} min="0"/>
        <Field label="Government bond value (KES)" value={values.bond} onChange={v=>updateValue("bond",v)} min="0"/>
        <Field label="Cash value (KES)" value={values.cash} onChange={v=>updateValue("cash",v)} min="0"/>
      </div>
      <div className="metric-grid">
        <Field label="Government bond expected return (%)" value={bondReturn} onChange={setBondReturn} min="-100" max="100"/>
        <Field label="Government bond volatility (%)" value={bondVol} onChange={setBondVol} min="0" max="100"/>
        <Field label="Cash expected return (%)" value={cashReturn} onChange={setCashReturn} min="-100" max="100"/>
        <Field label="Cash volatility (%)" value={cashVol} onChange={setCashVol} min="0" max="100"/>
      </div>
      {!valid||total<=0?<NoData message="Enter finite, non-negative KES position values and valid return and volatility assumptions. At least one position must have a positive value."/>:
      <Table headers={["Position","Value","Expected annual return","Return source"]} rows={alloc.map(row=>[
        row.name,money(row.value),pct(row.expected,3),row.isTbill?(row.latest?.date||"No CBK yield available"):"User assumption"
      ])}/>}
    </Panel>
    {valid&&total>0?<><Panel title="Portfolio intelligence summary" note="Weighted annual estimates based on the entered positions and available CBK bill yields">
      <div className="metric-grid">
        <Metric label="Portfolio value" value={money(total)}/>
        <Metric label="Weighted expected return" value={pct(expectedReturn,3)}/>
        <Metric label="Expected annual P&L" value={money(expectedPnl)}/>
        <Metric label="Number of positions" value={String(alloc.length)}/>
        <Metric label="Portfolio volatility" value={pct(portfolioVolatility,3)} note="Independent-position approximation"/>
        <Metric label="Parametric VaR · 95%" value={money(var95)} note="Daily horizon, normal approximation"/>
        <Metric label="Parametric VaR · 99%" value={money(var99)} note="Daily horizon, normal approximation"/>
        <Metric label="Diversification score" value={(diversification*100).toFixed(1)+"/100"} note="1 − sum of squared allocation weights"/>
      </div>
      <div className="dashboard-grid">
        <div>
          <div className="panel-title">Portfolio allocation</div>
          <ChartFrame height={270}><ResponsiveContainer><BarChart data={chart} layout="vertical"><CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e7edf2"/><XAxis type="number" tick={{fontSize:10,fill:"#8291a0"}} unit="%"/><YAxis dataKey="asset" type="category" tick={{fontSize:10,fill:"#8291a0"}} width={128}/><ChartTooltip/><Bar dataKey="value" name="Portfolio weight" fill="#16835d" radius={[0,4,4,0]}/></BarChart></ResponsiveContainer></ChartFrame>
        </div>
        <div>
          <div className="panel-title">Position contribution</div>
          <Table headers={["Position","Weight","Expected annual P&L"]} rows={alloc.map(row=>[row.name,pct(row.weight),money(row.annualPnl)])}/>
        </div>
      </div>
    </Panel>
    <Panel title="Concentration and CBK exposure" note="Portfolio shares are calculated from total entered KES value">
      <div className="metric-grid">
        <Metric label="Largest position" value={largest?.name||"—"}/>
        <Metric label="Largest position weight" value={largest?pct(largest.weight):"—"}/>
        <Metric label="Treasury bill exposure" value={money(tbillValue)}/>
        <Metric label="Treasury bill share" value={pct(tbillWeight)}/>
      </div>
      <p className="panel-note">{largest&&largest.weight>=.6?"Concentration is high: one position represents at least 60% of this portfolio.":largest&&largest.weight>=.4?"Concentration is moderate: the largest position represents between 40% and 60%.":"No single position exceeds 40% of the entered portfolio."} {tbillWeight>=.7?"The portfolio is heavily exposed to Treasury bills; reinvestment conditions and CBK auction rates may materially affect future returns.":tbillWeight>=.4?"Treasury bills form a significant portion of the allocation.":"Treasury bill exposure is below 40% of the entered portfolio."}</p>
    </Panel>
    <Panel title="Historical CBK risk contribution" note="Yield-change volatility is calculated from successive auction-rate differences">
      {riskRows.length?<Table headers={["Treasury bill","Portfolio weight","Latest CBK yield","Yield-change volatility","Price-risk volatility proxy","Weighted contribution"]} rows={riskRows.map(row=>[
        row.name,pct(row.weight),row.yield===null?"—":pct(row.yield,4),pct(row.volatility,4),pct(row.priceVolatility,4),pct(row.contribution,4)
      ])}/>:<NoData message="No Treasury bill positions have been entered. Add a bill position to display its historical CBK yield risk contribution."/>}
      <p className="panel-note">Treasury bill portfolio risk uses a duration-based price-change proxy derived from successive CBK auction-yield changes and the actual spacing between observations. The risk table also shows raw yield-change volatility, matching the retained CBK module. This is not a traded total-return series. Bond and cash volatility are user assumptions. Portfolio VaR uses an independent-position, normal approximation.</p>
    </Panel></>:null}
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
  const valid=Number.isFinite(initial)&&initial>0&&perPair.every(row=>Number.isFinite(row.weight)&&row.weight>=0)&&Number.isFinite(weightSum)&&Math.abs(weightSum-100)<.0001;
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

function escapeHtml(value:unknown){
  return String(value??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;");
}
function htmlTable(headers:string[],rows:(string|number)[][]){
  return "<table><thead><tr>"+headers.map(value=>"<th>"+escapeHtml(value)+"</th>").join("")+"</tr></thead><tbody>"+
    rows.map(row=>"<tr>"+row.map(value=>"<td>"+escapeHtml(value)+"</td>").join("")+"</tr>").join("")+
    "</tbody></table>";
}
function htmlDownload(filename:string,html:string){
  const blob=new Blob([html],{type:"text/html;charset=utf-8"});
  const url=URL.createObjectURL(blob),link=document.createElement("a");
  link.href=url;link.download=filename;link.click();URL.revokeObjectURL(url);
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
  const fxReportRows=fx.map(x=>[x.pair,x.rows.at(-1)?.date||"—",x.latest?.toFixed(4)||"—",pct(x.change),pct(x.vol),x.rows.length,x.rows.at(-1)?.source||"—"]);
  const billReportRows=latestBills.map(row=>[row.tenor_days+" days",row.date,pct(row.rate,4),row.issue_number||"—",row.source]);
  const htmlReport="<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Kenya Financial Analytics — Market Report</title><style>body{font:14px/1.6 Inter,Segoe UI,Arial,sans-serif;color:#1c3040;max-width:1100px;margin:40px auto;padding:0 24px}h1{font-size:28px;letter-spacing:-.5px}h2{font-size:17px;margin-top:32px}p,small{color:#647585}.meta{border-bottom:1px solid #dce4ea;padding-bottom:18px}table{width:100%;border-collapse:collapse;margin:12px 0 22px;font-size:12px}th,td{text-align:left;padding:9px;border-bottom:1px solid #e3e9ed}th{background:#f3f6f8;color:#44586a;font-weight:700}footer{border-top:1px solid #dce4ea;margin-top:36px;padding-top:16px;color:#647585;font-size:11px}</style></head><body><h1>Kenya Financial Analytics</h1><div class='meta'><strong>Market snapshot</strong><br>Generated: "+escapeHtml(generated)+"<br>FX latest observation: "+escapeHtml(data.health.latest_fx_observation||"Not available")+"<br>Treasury bill latest auction: "+escapeHtml(data.health.latest_bill_observation||"Not available")+"<br>Data source: Central Bank of Kenya</div><h2>Foreign exchange overview</h2>"+htmlTable(["Pair","Latest date","Latest rate","Cumulative change","Annualised volatility","Observations","Source"],fxReportRows)+"<h2>Latest Treasury bill auction</h2>"+htmlTable(["Tenor","Auction date","Market-weighted yield","Issue number","Source"],billReportRows)+"<h2>Data coverage and limitations</h2><p>The figures in this report are based on stored observations attributed to the Central Bank of Kenya. Coverage differs by instrument. Missing auction dates and tenors are not interpolated in the historical tables. Intermediate rates, where shown in the Yield Curve workspace, are model estimates and are identified separately. Volatility is a historical statistic, not a forward-looking forecast.</p><footer>Kenya Financial Analytics · For research and information only. Not investment advice.</footer></body></html>";
  return <div className="workspace-stack">
    <Panel title="Market research report" note={"Generated "+generated+" · Source: Central Bank of Kenya"}>
      <div className="metric-grid"><Metric label="FX observations" value={data.fx.length.toLocaleString("en-KE")}/><Metric label="Auction observations" value={data.bills.length.toLocaleString("en-KE")}/><Metric label="FX coverage" value={(data.fx.map(x=>x.date).sort()[0]||"—")+" to "+(data.health.latest_fx_observation||"—")}/><Metric label="Auction coverage" value={(dates[0]||"—")+" to "+(data.health.latest_bill_observation||"—")}/></div>
      <div className="panel-head"><div><div className="panel-title">Currency market summary</div><div className="panel-note">Cumulative change over each series' available period</div></div><div style={{display:"flex",gap:8,flexWrap:"wrap"}}><button className="primary-btn" onClick={()=>csvDownload("kenya-financial-analytics-report.csv",["Section","Instrument","Latest date","Latest value","Cumulative change","Annualised volatility","Observations","Source","Source URL"],exportRows)}>Download report CSV</button><button className="theme-button" onClick={()=>htmlDownload("kenya-financial-analytics-report.html",htmlReport)}>Download HTML report</button></div></div>
      <Table headers={["Pair","Latest date","Latest rate","Cumulative change","Annualised volatility","Observations","Source"]} rows={fx.map(x=>[x.pair,x.rows.at(-1)?.date||"—",x.latest?.toFixed(4)||"—",pct(x.change),pct(x.vol),x.rows.length,x.rows.at(-1)?.source||"—"])}/>
    </Panel>
    <Panel title="Latest Treasury bill auction snapshot" note={latestDate||"No auction results in database"}>
      <Table headers={["Tenor","Auction date","Market-weighted yield","Issue number","Source"]} rows={latestBills.map(row=>[row.tenor_days+" days",row.date,pct(row.rate,4),row.issue_number||"—",row.source])}/>
    </Panel>
    <Panel title="Source and limitations" note="Report provenance">
      <p style={{fontSize:12,lineHeight:1.7,color:"var(--muted)",margin:0}}>Market values in this report are stored observations attributed to the Central Bank of Kenya. Data coverage may differ by instrument. No rates are estimated for missing dates or tenors. Volatility is calculated from observed daily FX changes and is not a forward-looking risk forecast.</p>
    </Panel>
  </div>;
}

function Backtesting({data}:{data:MarketPayload}){
  const [mode,setMode]=useState("FX moving average");
  const [pair,setPair]=useState("USD/KES"),[tenor,setTenor]=useState("91");
  const [short,setShort]=useState("20"),[long,setLong]=useState("60"),[fee,setFee]=useState("0"),[duration,setDuration]=useState("5");
  const fx=seriesFor(data.fx,pair);
  const billRows=data.bills.filter(row=>row.tenor_days===Number(tenor)).sort((a,b)=>a.date.localeCompare(b.date));
  const values=mode==="FX moving average"?fx.values:billRows.map(row=>row.rate);
  const dates=mode==="FX moving average"?fx.rows.map(row=>row.date):billRows.map(row=>row.date);
  const s=Number(short),l=Number(long),cost=Number(fee)/10000,rateDuration=Number(duration);
  const isFx=mode==="FX moving average";
  const valid=isFx
    ? Number.isInteger(s)&&Number.isInteger(l)&&s>=2&&l>s&&Number.isFinite(cost)&&cost>=0&&cost<=.1&&values.length>l+1
    : Number.isInteger(s)&&s>=2&&Number.isFinite(rateDuration)&&rateDuration>0&&rateDuration<=100&&Number.isFinite(cost)&&cost>=0&&cost<=.1&&values.length>s+1;
  const points=[];
  let equity=1,benchmark=1,position=0,trades=0,peak=1,worst=0;
  for(let i=1;valid&&i<values.length;i++){
    let signal=0;
    if(isFx){
      if(i>=l&&mean(values.slice(i-s,i))>mean(values.slice(i-l,i)))signal=1;
    }else if(i>s&&values[i-1]>mean(values.slice(i-s-1,i-1))){
      signal=1;
    }
    const changed=signal!==position;
    if(changed){if(signal===1)trades++;position=signal;}
    const baseReturn=isFx
      ? (values[i-1]===0?0:values[i]/values[i-1]-1)
      : -rateDuration*(values[i]-values[i-1]);
    const strategyReturn=position?baseReturn-(changed?cost:0):0;
    equity*=1+strategyReturn;benchmark*=1+baseReturn;peak=Math.max(peak,equity);worst=Math.min(worst,equity/peak-1);
    points.push({date:dates[i],strategy:equity,benchmark});
  }
  const strategyReturn=equity-1,benchmarkReturn=benchmark-1;
  return <div className="workspace-stack">
    <Panel title="Historical strategy test" note="Each signal is formed from information available before the return being measured">
      <div className="metric-grid">
        <label className="field"><span>Backtest mode</span><select className="search" value={mode} onChange={e=>setMode(e.target.value)}><option>FX moving average</option><option>Treasury bill yield momentum</option></select></label>
        {isFx
          ? <label className="field"><span>Currency pair</span><select className="search" value={pair} onChange={e=>setPair(e.target.value)}>{PAIRS.map(x=><option key={x}>{x}</option>)}</select></label>
          : <label className="field"><span>Treasury bill tenor</span><select className="search" value={tenor} onChange={e=>setTenor(e.target.value)}>{TENORS.map(x=><option key={x} value={x}>{x} days</option>)}</select></label>}
        <Field label={isFx?"Short average (observations)":"Yield-momentum lookback"} value={short} onChange={setShort} min="2" max="1000" step="1"/>
        {isFx?<Field label="Long average (observations)" value={long} onChange={setLong} min="3" max="1000" step="1"/>:<Field label="Price sensitivity multiplier" value={duration} onChange={setDuration} min="0.01" max="100"/>}
        <Field label="Cost per position change (basis points)" value={fee} onChange={setFee} min="0" max="1000"/>
      </div>
      {valid?<div className="metric-grid">
        <Metric label="Strategy cumulative return" value={pct(strategyReturn)} note={isFx?"Long / cash FX moving-average rule":"Long / cash yield-momentum proxy"}/>
        <Metric label={isFx?"Buy-and-hold return":"Continuous exposure proxy"} value={pct(benchmarkReturn)}/>
        <Metric label="Strategy max drawdown" value={pct(worst)}/>
        <Metric label="Entries" value={trades.toString()} note="Entries from cash into the model position"/>
      </div>:<NoData message={isFx?"The short window must be below the long window, with enough observations for both windows.":"Choose a valid lookback and price-sensitivity multiplier; the selected Treasury-bill tenor needs more historical observations than the lookback."}/>}
      {points.length?<ChartFrame height={320}><ResponsiveContainer><LineChart data={points}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7edf2"/><XAxis dataKey="date" minTickGap={25} tick={{fontSize:10,fill:"#8291a0"}}/><YAxis tick={{fontSize:10,fill:"#8291a0"}}/><ChartTooltip/><Line dataKey="strategy" name="Strategy index" stroke="#087f8c" strokeWidth={2} dot={false}/><Line dataKey="benchmark" name={isFx?"Buy-and-hold index":"Continuous exposure index"} stroke="#9aa6b2" strokeWidth={1.7} dot={false}/></LineChart></ResponsiveContainer></ChartFrame>:null}
    </Panel>
    <Panel title="Method and limitations" note="Research simulation only; no trades are placed">
      {isFx?<Table headers={["Rule","Implementation"]} rows={[
        ["Entry","Prior short-window average above prior long-window average"],
        ["Position","Long the selected FX reference series while the signal is positive; otherwise cash"],
        ["Timing","Signal uses only observations available before the return being measured"],
        ["Trading cost","User-specified basis points on each entry or exit"],
        ["Excluded factors","Spread, slippage, funding, taxes, liquidity and execution constraints"]
      ]}/>:<Table headers={["Rule","Implementation"]} rows={[
        ["Entry","Previous observed yield above the mean of the prior lookback window"],
        ["Position","Long a duration-based price proxy while the yield-momentum signal is positive; otherwise cash"],
        ["Price approximation","Daily price return ≈ − sensitivity multiplier × change in yield"],
        ["Timing","Signal uses prior yields before the current yield change is applied"],
        ["Trading cost","User-specified basis points on each entry or exit"],
        ["Excluded factors","Actual bill pricing, reinvestment, taxes, liquidity, bid–ask spreads and settlement costs"]
      ]}/>}
      <p className="panel-note">{isFx?"The FX backtest uses observed exchange-rate returns.":"The Treasury bill strategy is a simplified price-sensitivity proxy based on the original yield-momentum engine; it is not an exact Treasury bill total-return series."} Both outputs are historical simulations and should not be interpreted as forecasts.</p>
    </Panel>
  </div>;
}

function StressTesting({data}:{data:MarketPayload}){
  const [capital,setCapital]=useState("1000000"),[fxShock,setFxShock]=useState("-10");
  const [bondValue,setBondValue]=useState("400000"),[duration,setDuration]=useState("4.5"),[convexity,setConvexity]=useState("25");
  const [tbillValue,setTbillValue]=useState("600000"),[tbillTenor,setTbillTenor]=useState("91"),[tbillRateOverride,setTbillRateOverride]=useState("");
  const value=Number(capital),shock=Number(fxShock)/100;
  const bond=Number(bondValue),mod=Number(duration),conv=Number(convexity);
  const tbill=Number(tbillValue),tenor=Number(tbillTenor);
  const latestDate=data.bills.reduce((latest,row)=>!latest||row.date>latest?row.date:latest,"");
  const latestAuction=data.bills.filter(row=>row.date===latestDate);
  const selectedBill=latestAuction.find(row=>row.tenor_days===tenor)||data.bills.filter(row=>row.tenor_days===tenor).sort((x,y)=>x.date.localeCompare(y.date)).at(-1);
  const effectiveRate=tbillRateOverride===""?(selectedBill?.rate??.09):Number(tbillRateOverride)/100;
  const valid=[value,shock,bond,mod,conv,tbill,tenor,effectiveRate].every(Number.isFinite)&&value>0&&shock>-1&&shock<=5&&bond>0&&mod>=0&&mod<=100&&conv>=0&&conv<=10000&&tbill>=0&&[91,182,364].includes(tenor)&&effectiveRate>=0&&effectiveRate<=1;
  const stressed=value*(1+shock);
  const scenarios=[-30,-20,-15,-10,-5,0,5,10,15,20].map(x=>({shock:x,value:value*(1+x/100),pnl:value*x/100}));
  const startingFixedIncome=bond+tbill;
  const cbkScenarios=[{name:"CBK +50 bps",change:.005},{name:"CBK +100 bps",change:.01},{name:"CBK +200 bps",change:.02},{name:"CBK −50 bps",change:-.005},{name:"CBK −100 bps",change:-.01}];
  const fixedIncomeRows=cbkScenarios.map(item=>{
    const bondMove=-mod*item.change+.5*conv*item.change**2;
    const bondPnl=bond*bondMove;
    const newRate=effectiveRate+item.change;
    const tbillIncomeNow=tbill*effectiveRate*tenor/365;
    const tbillIncomeStressed=tbill*newRate*tenor/365;
    const tbillPnl=tbillIncomeStressed-tbillIncomeNow;
    return {name:item.name,change:item.change,bondPnl,tbillPnl,totalPnl:bondPnl+tbillPnl,ending:startingFixedIncome+bondPnl+tbillPnl};
  });
  const curveRates=[91,182,364].map(days=>({days,row:latestAuction.find(x=>x.tenor_days===days)})).filter(x=>x.row);
  const curveRows=curveRates.map(({days,row})=>{
    const shortChange=days<=182?-.005:.005;
    const flatChange=-shortChange;
    return {days,current:row!.rate,steep:row!.rate+shortChange,flat:row!.rate+flatChange};
  });
  return <div className="workspace-stack">
    <Panel title="Capital market shock" note="Apply a direct percentage shock to a user-entered portfolio reference value">
      <div className="metric-grid"><Field label="Reference portfolio value (KES)" value={capital} onChange={setCapital} min="1"/><Field label="Market shock (%)" value={fxShock} onChange={setFxShock} min="-99" max="500"/></div>
      {Number.isFinite(value)&&value>0&&Number.isFinite(shock)&&shock>-1&&shock<=5?<><div className="metric-grid"><Metric label="Starting value" value={money(value)}/><Metric label="Profit / loss" value={money(stressed-value)}/><Metric label="Stressed value" value={money(stressed)}/><Metric label="Applied shock" value={pct(shock)}/></div><Table headers={["Scenario","Profit / loss","Stressed value"]} rows={scenarios.map(row=>[row.shock+"%",money(row.pnl),money(row.value)])}/></>:<NoData message="Use a positive reference value and a market shock above −100% and no greater than +500%."/>}
    </Panel>
    <Panel title="CBK rate scenarios" note="Combined bond duration-convexity impact and Treasury bill reinvestment-income change">
      <div className="metric-grid">
        <Field label="Bond market value (KES)" value={bondValue} onChange={setBondValue} min="1"/>
        <Field label="Modified duration" value={duration} onChange={setDuration} min="0" max="100"/>
        <Field label="Convexity" value={convexity} onChange={setConvexity} min="0" max="10000"/>
        <Field label="Treasury bill principal (KES)" value={tbillValue} onChange={setTbillValue} min="0"/>
        <label className="field"><span>Treasury bill tenor</span><select className="search" value={tbillTenor} onChange={e=>setTbillTenor(e.target.value)}>{TENORS.map(t=><option key={t} value={t}>{t} days</option>)}</select></label>
        <Field label="Current Treasury bill yield (%)" value={tbillRateOverride===""?(selectedBill?(selectedBill.rate*100).toFixed(4):"9.0000"):tbillRateOverride} onChange={setTbillRateOverride} min="0" max="100"/>
      </div>
      {valid?<><div className="metric-grid"><Metric label="Fixed-income starting value" value={money(startingFixedIncome)}/><Metric label="CBK yield used" value={pct(effectiveRate,4)} note={selectedBill?.date||"User-entered rate"}/><Metric label="Bond exposure" value={money(bond)}/><Metric label="T-bill reinvestment exposure" value={money(tbill)}/></div>
      <Table headers={["Scenario","Rate change","Bond price impact","T-bill income change","Combined P/L","Stressed value"]} rows={fixedIncomeRows.map(row=>[
        row.name,pp(row.change,2),money(row.bondPnl),money(row.tbillPnl),money(row.totalPnl),money(row.ending)
      ])}/></>:<NoData message="Check all fixed-income inputs. Values must be finite, duration and convexity non-negative, tenor supported, and yield between 0% and 100%."/>}
      <p className="panel-note">Bond impacts use the duration-convexity approximation. Treasury bill effects represent a simple reinvestment-income change over the selected bill tenor, not a mark-to-market price change.</p>
    </Panel>
    <Panel title="Yield-curve shape scenarios" note={"Parallel curve observations from the latest matched CBK auction · "+(latestDate||"No auction data")}>
      {curveRows.length>=2?<Table headers={["Tenor","Current yield","Steepening scenario","Flattening scenario"]} rows={curveRows.map(row=>[
        row.days+" days",pct(row.current,4),pct(row.steep,4),pct(row.flat,4)
      ])}/>:<NoData message="At least two same-date Treasury bill tenors are required for curve scenarios."/>}
      <p className="panel-note">Steepening lowers short-tenor yields by 50 basis points and raises the 364-day yield by 50 basis points. Flattening applies the reverse shock. This is deterministic scenario analysis, not a forecast.</p>
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
    case "Stress Testing":return <StressTesting data={payload}/>;
    default:return <Panel title={name}><NoData message="This module is not available in this build."/></Panel>;
  }
}
