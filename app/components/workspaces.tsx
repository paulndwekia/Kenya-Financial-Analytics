"use client";

import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  treasuryBillPrice, bondCashFlows, bondPrice, bondYtm, bondMetrics,
  bondPriceSensitivity, blackScholes, historicalVaR, parametricVaR,
  expectedShortfall, annualizedVolatility, sharpeRatio, sortinoRatio,
  yieldCurveSlopes, classifyYieldCurve, interpolateYield, simpleForwardRate,
  bondPriceShock, treasuryBillReinvestmentShock, cbkRateScenarios,
  curveScenario, portfolioMetrics, applyShock
} from "../../lib/finance.mjs";
import { motion } from "motion/react";
import {
  Activity, ArrowDownRight, ArrowUpRight, BarChart3, BookOpen, BriefcaseBusiness,
  ChartNoAxesCombined, CircleDollarSign, FileText, Gauge, Globe2, Layers3,
  Search, ShieldCheck, TrendingUp, Wallet, Zap
} from "lucide-react";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ComposedChart, Line, LineChart,
  ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis
} from "recharts";

export type FxRow = {date:string; instrument:string; value:number; source:string; source_url?:string|null};
export type BillRow = {date:string; tenor_days:number; rate:number; price?:number|null; amount_offered?:number|null; amount_accepted?:number|null; issue_number?:string|null; source:string; source_url?:string|null};
export type MarketPayload = {
  ok:boolean; fx:FxRow[]; bills:BillRow[]; source:string; retrieved_at:string|null;
  health:{database?:string;database_connected?:boolean;fx_rows:number;bills_rows:number;latest_fx_observation?:string|null;latest_bill_observation?:string|null;last_refresh?:{status:string;started_at:string|null;completed_at:string|null;source:string;fx_rows_upserted:number;bill_rows_upserted:number}|null;warnings?:string[]};
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
  {name:"Risk Intelligence",group:"Risk",desc:"Compare realised volatility and drawdown across tracked currency pairs.",icon:ShieldCheck,color:"#c18a35"},
  {name:"Stress Testing",group:"Risk",desc:"Apply explicit shocks to capital and modelled bond values.",icon:Activity,color:"#c45151"},
  {name:"Portfolio Intelligence",group:"Portfolio",desc:"Model a Kenyan fixed-income allocation and inspect yield, concentration and risk.",icon:BriefcaseBusiness,color:"#16835d"},
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
function Panel({title,note,children,action}:{title:string;note?:string;children:ReactNode;action?:ReactNode}){
  return <section className="panel"><div className="panel-head"><div><div className="panel-title">{title}</div>{note&&<div className="panel-note">{note}</div>}</div>{action}</div>{children}</section>;
}
function ChartFrame({children,height=280,className}:{children:ReactNode;height?:number;className?:string}){
  return <div className={className} style={{width:"100%",height}}>{children}</div>;
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
  const fx=data?.fx||[];
  const bills=data?.bills||[];
  const latestBills=useMemo(()=>{
    const latestDate=bills.reduce((latest,row)=>!latest||row.date>latest?row.date:latest,"");
    return bills.filter(row=>row.date===latestDate).sort((x,y)=>x.tenor_days-y.tenor_days);
  },[bills]);

  const quoteCards=PAIRS.map(pair=>{
    const rows=pairRows(fx,pair);
    const latest=rows.at(-1);
    const previous=rows.at(-2);
    const dailyChange=latest&&previous&&previous.value!==0?latest.value/previous.value-1:null;
    return {pair,latest,dailyChange};
  });

  const indexedHistory=useMemo(()=>{
    const pairHistory=PAIRS.map(pair=>({pair,rows:pairRows(fx,pair).slice(-50)}));
    const firstByPair=new Map(pairHistory.map(item=>[item.pair,item.rows[0]?.value||null]));
    const byDate=new Map<string,Record<string,number|string|null>>();
    for(const item of pairHistory){
      const base=firstByPair.get(item.pair);
      if(!base)continue;
      for(const row of item.rows){
        if(!byDate.has(row.date))byDate.set(row.date,{date:row.date});
        byDate.get(row.date)![item.pair]=row.value/base*100;
      }
    }
    return [...byDate.values()].sort((x,y)=>String(x.date).localeCompare(String(y.date)));
  },[fx]);

  const latestAuctionDate=latestBills[0]?.date||null;
  const presentTenors=latestBills.length;
  const refresh=data?.health?.last_refresh||null;
  const importStatus=refresh?.status||"not recorded";
  const statusLabel=importStatus==="success"?"Successful":importStatus==="partial"?"Partially successful":importStatus==="failed"?"Failed":importStatus==="running"?"In progress":"Not recorded";
  const statusClass=importStatus==="success"?"health-good":importStatus==="partial"?"health-warning":importStatus==="failed"?"health-bad":"health-neutral";

  return <div className="workspace-stack dashboard-workspace">
    <div className="dashboard-quote-grid">
      {quoteCards.map(({pair,latest,dailyChange})=>
        <div className="dashboard-quote-card" key={pair}>
          <div className="dashboard-quote-top"><span>{pair}</span><span className="dashboard-quote-date">{latest?.date||"No CBK data"}</span></div>
          <div className="dashboard-quote-value">{latest?latest.value.toFixed(4):"—"}</div>
          <div className="dashboard-quote-bottom">
            <span>Daily movement</span>
            {dailyChange===null?<span className="dashboard-quote-flat">—</span>:<span className={dailyChange>0?"dashboard-change dashboard-change-up":dailyChange<0?"dashboard-change dashboard-change-down":"dashboard-quote-flat"}>{dailyChange>0?"+":""}{pct(dailyChange,3)} · {dailyChange>0?"KES weaker":dailyChange<0?"KES firmer":"Unchanged"}</span>}
          </div>
        </div>
      )}
    </div>

    <div className="dashboard-grid dashboard-market-grid">
      <Panel title="KES exchange-rate performance" note="Relative index · first observation in each displayed series = 100">
        {indexedHistory.length>1?<ChartFrame height={310} className="dashboard-index-chart"><ResponsiveContainer><LineChart data={indexedHistory} margin={{top:12,right:12,bottom:4,left:2}}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7edf2"/>
          <XAxis dataKey="date" minTickGap={26} tick={{fontSize:10,fill:"#8291a0"}} axisLine={false} tickLine={false}/>
          <YAxis tick={{fontSize:10,fill:"#8291a0"}} domain={["auto","auto"]} width={48}/>
          <ReferenceLine y={100} stroke="#9aa6b2" strokeDasharray="4 4"/>
          <ChartTooltip/>
          <Line type="monotone" dataKey="USD/KES" name="USD/KES" stroke="#087f8c" strokeWidth={2.2} dot={false} connectNulls={false} activeDot={{r:4}}/>
          <Line type="monotone" dataKey="GBP/KES" name="GBP/KES" stroke="#356bb3" strokeWidth={2.2} dot={false} connectNulls={false} activeDot={{r:4}}/>
          <Line type="monotone" dataKey="EUR/KES" name="EUR/KES" stroke="#d5a43b" strokeWidth={2.2} dot={false} connectNulls={false} activeDot={{r:4}}/>
        </LineChart></ResponsiveContainer></ChartFrame>:<NoData message="At least two observations per currency pair are needed for the relative performance view."/>}
        <p className="panel-note">The index makes percentage movement comparable across pairs with different quote levels. It is a historical comparison, not a currency forecast.</p>
      </Panel>

      <Panel title="Latest Treasury bill auction" note={latestAuctionDate||"No auction records"}>
        <div className="market-list">
          {TENORS.map(tenor=>{
            const row=latestBills.find(item=>item.tenor_days===tenor);
            return <div className="market-row dashboard-bill-row" key={tenor}>
              <div className="instrument">{tenor}-day<small>{row?.issue_number||"No issue reference"}</small></div>
              <div className="rate">{row?pct(row.rate,4):"—"}</div>
              <div className="panel-note">{row?.date||"No result"}</div>
            </div>;
          })}
        </div>
        <div className={presentTenors===TENORS.length?"dashboard-auction-note":"dashboard-auction-note warning"}>
          {presentTenors===TENORS.length?"All three tenors are available for this auction.":presentTenors+" of "+TENORS.length+" tenors are recorded for this auction date."}
        </div>
        <p className="panel-note">CBK market-weighted accepted yields. Different auction dates are not combined into one curve.</p>
      </Panel>
    </div>

    <Panel title="Market data operations" note="Database status and latest recorded CBK import attempt">
      <div className="dashboard-health-grid">
        <div className="dashboard-health-item"><span className="dashboard-health-label">Database connection</span><strong>{data?.health?.database_connected?"Connected":"Unavailable"}</strong><small>{data?.health?.database||"Waiting for database response"}</small></div>
        <div className="dashboard-health-item"><span className="dashboard-health-label">Latest import attempt</span><strong className={statusClass}>{statusLabel}</strong><small>{refresh?.completed_at?new Date(refresh.completed_at).toLocaleString("en-KE"):refresh?.started_at?"Started "+new Date(refresh.started_at).toLocaleString("en-KE"):"No import attempt recorded"}</small></div>
        <div className="dashboard-health-item"><span className="dashboard-health-label">FX records stored</span><strong>{(data?.health?.fx_rows||0).toLocaleString("en-KE")}</strong><small>Latest observation · {data?.health?.latest_fx_observation||"—"}</small></div>
        <div className="dashboard-health-item"><span className="dashboard-health-label">Auction records stored</span><strong>{(data?.health?.bills_rows||0).toLocaleString("en-KE")}</strong><small>Latest observation · {data?.health?.latest_bill_observation||"—"}</small></div>
      </div>
      {refresh&&<div className="dashboard-import-foot"><span>Last attempt source: {refresh.source}</span><span>{refresh.fx_rows_upserted.toLocaleString("en-KE")} FX rows · {refresh.bill_rows_upserted.toLocaleString("en-KE")} auction rows reported</span></div>}
      {data?.health?.warnings?.length?data.health.warnings.map((warning,index)=><p className="dashboard-warning" key={index}>{warning}</p>):null}
      {loading&&<p className="panel-note">Refreshing market data from the connected database…</p>}
      {!refresh&&<p className="panel-note">A database connection confirms storage availability; it does not by itself confirm that a fresh CBK import has run.</p>}
    </Panel>
  </div>;
}
function KenyanMarket({data}:{data:MarketPayload}){
  const [pair,setPair]=useState<string>("USD/KES");
  const [window,setWindow]=useState("90D");
  const allRows=seriesFor(data.fx,pair).rows;
  const latest=allRows.at(-1);
  const previous=allRows.at(-2);
  const dailyChange=latest&&previous&&previous.value!==0?latest.value/previous.value-1:null;
  const dailyAbsolute=latest&&previous?latest.value-previous.value:null;

  const days=window==="30D"?30:window==="90D"?90:window==="180D"?180:window==="1Y"?365:null;
  const cutoff=latest&&days?new Date(Date.parse(latest.date+"T00:00:00Z")-days*86400000).toISOString().slice(0,10):null;
  const rows=allRows.filter(row=>!cutoff||row.date>=cutoff);
  const values=rows.map(row=>row.value);
  const rets=returns(values);
  const periodStart=rows[0];
  const periodChange=periodStart&&latest&&periodStart.value!==0?latest.value/periodStart.value-1:null;
  const high=values.length?Math.max(...values):null;
  const low=values.length?Math.min(...values):null;
  const highDate=high===null?null:rows.find(row=>row.value===high)?.date||null;
  const lowDate=low===null?null:rows.find(row=>row.value===low)?.date||null;
  const recent=[...rows].slice(-12).reverse();
  const recentRows=recent.map(row=>{
    const index=allRows.findIndex(item=>item.date===row.date&&item.value===row.value);
    const prior=index>0?allRows[index-1]:null;
    const change=prior&&prior.value!==0?row.value/prior.value-1:null;
    return [row.date,row.instrument,row.value.toFixed(4),change===null?"—":pct(change,3),row.source];
  });
  const chart=rows.map(row=>({date:row.date,rate:row.value}));
  const rangeLabel=window==="ALL"?"All available history":window==="1Y"?"Last 12 months":"Last "+window.replace("D"," days");

  return <div className="workspace-stack kenyan-market-workspace">
    <Panel title="Currency-pair profile" note="A focused view of the selected CBK exchange-rate series">
      <div className="market-detail-controls">
        <label className="field"><span>Currency pair</span><select className="search" aria-label="Currency pair" value={pair} onChange={event=>setPair(event.target.value)}>{PAIRS.map(value=><option key={value} value={value}>{value}</option>)}</select></label>
        <div className="market-range-group" role="group" aria-label="Observation window">
          {["30D","90D","180D","1Y","ALL"].map(value=><button key={value} type="button" className={window===value?"active":""} aria-pressed={window===value} onClick={()=>setWindow(value)}>{value==="ALL"?"All":value}</button>)}
        </div>
      </div>
      <div className="market-detail-metrics">
        <Metric label="Latest CBK rate" value={latest?latest.value.toFixed(4):"—"} note={latest?.date||"No stored observation"}/>
        <Metric label="Daily movement" value={dailyChange===null?"—":(dailyChange>0?"+":"")+pct(dailyChange,3)} note={dailyChange===null?"Previous observation unavailable":dailyChange>0?"KES weakened against this pair":dailyChange<0?"KES strengthened against this pair":"No change"}/>
        <Metric label="Period movement" value={periodChange===null?"—":(periodChange>0?"+":"")+pct(periodChange,3)} note={periodStart?.date&&latest?.date?periodStart.date+" to "+latest.date:rangeLabel}/>
        <Metric label="Annualised volatility" value={rets.length>1?pct(stdev(rets)*Math.sqrt(252)):"—"} note="Sample daily-return standard deviation × √252"/>
        <Metric label="Maximum quote drawdown" value={values.length>1?pct(maxDrawdown(values)):"—"} note="Peak-to-trough decline in the quoted rate"/>
      </div>
      <div className="market-period-meta">
        <span>{rangeLabel} · {rows.length.toLocaleString("en-KE")} observations</span>
        <span>{periodStart?.date||"—"} to {latest?.date||"—"}</span>
      </div>
    </Panel>

    <div className="market-detail-grid">
      <Panel title={pair+" rate history"} note="Kenyan shillings per one unit of foreign currency">
        {chart.length>1?<ChartFrame height={320} className="market-detail-chart"><ResponsiveContainer><AreaChart data={chart} margin={{top:10,right:12,bottom:4,left:0}}>
          <defs><linearGradient id="pairHistoryFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#087f8c" stopOpacity={.2}/><stop offset="95%" stopColor="#087f8c" stopOpacity={0}/></linearGradient></defs>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7edf2"/>
          <XAxis dataKey="date" minTickGap={24} tick={{fontSize:10,fill:"#8291a0"}} axisLine={false} tickLine={false}/>
          <YAxis domain={["auto","auto"]} tick={{fontSize:10,fill:"#8291a0"}} width={60} tickFormatter={value=>Number(value).toFixed(1)}/>
          <ChartTooltip/>
          {high!==null&&<ReferenceLine y={high} stroke="#d5a43b" strokeDasharray="4 4" label={{value:"Period high",position:"insideTopRight",fontSize:9,fill:"#a27a24"}}/>}
          <Area type="monotone" dataKey="rate" name="KES per unit" stroke="#087f8c" strokeWidth={2.2} fill="url(#pairHistoryFill)" activeDot={{r:4}}/>
        </AreaChart></ResponsiveContainer></ChartFrame>:<NoData message="This pair has fewer than two observations in the selected window. Choose a longer period or wait for more published CBK records."/>}
        <p className="panel-note">A rising quote means more KES are required to buy one unit of foreign currency. It indicates a weaker shilling; a falling quote indicates a firmer shilling.</p>
      </Panel>

      <Panel title="Recent CBK observations" note="Latest 12 records within the selected window">
        {recentRows.length?<div className="market-recent-table"><Table headers={["Date","Pair","Rate","Daily move","Publisher"]} rows={recentRows}/></div>:<NoData message="No observations are available for this pair and window."/>}
        <div className="market-range-extremes">
          <div><span>Period high</span><strong>{high===null?"—":high.toFixed(4)}</strong><small>{highDate||"—"}</small></div>
          <div><span>Period low</span><strong>{low===null?"—":low.toFixed(4)}</strong><small>{lowDate||"—"}</small></div>
        </div>
        <p className="panel-note">The drawdown statistic describes the exchange-rate quote path. It is not a loss calculation for a foreign-currency holder or a diversified investment portfolio.</p>
      </Panel>
    </div>
  </div>;
}
function MarketIntelligence({data}:{data:MarketPayload}){
  const [horizon,setHorizon]=useState(20);
  const windowOptions=[5,20,60];
  const pairSeries=PAIRS.map(pair=>{
    const observations=pairRows(data.fx,pair);
    const closes=observations.map(row=>row.value);
    const dailyReturns=returns(closes);
    const latest=observations.at(-1);
    const previous=observations.at(-2);
    const intervals=Math.min(horizon,Math.max(0,observations.length-1));
    const base=intervals?closes[closes.length-1-intervals]:undefined;
    const momentum=base&&base!==0&&latest?latest.value/base-1:null;
    const dailyMove=latest&&previous&&previous.value!==0?latest.value/previous.value-1:null;
    const volatility=dailyReturns.length>1?stdev(dailyReturns)*Math.sqrt(252):null;
    return {pair,observations,closes,dailyReturns,latest,previous,dailyMove,momentum,volatility,intervals};
  });

  const correlationRows=useMemo(()=>{
    const maps=PAIRS.map(pair=>{
      const observations=pairRows(data.fx,pair);
      const map=new Map<string,number>();
      for(let i=1;i<observations.length;i++){
        const prev=observations[i-1],current=observations[i];
        if(prev.value>0&&current.value>0)map.set(current.date,current.value/prev.value-1);
      }
      return {pair,map};
    });
    const correlations=maps.map((left,i)=>maps.map((right,j)=>{
      const common=[...left.map.keys()].filter(date=>right.map.has(date));
      if(i===j)return {value:1,count:common.length};
      if(common.length<3)return {value:null,count:common.length};
      const xs=common.map(date=>left.map.get(date)!),ys=common.map(date=>right.map.get(date)!);
      const mx=mean(xs),my=mean(ys);
      const sx=Math.sqrt(mean(xs.map(x=>(x-mx)**2))),sy=Math.sqrt(mean(ys.map(y=>(y-my)**2)));
      const covariance=mean(xs.map((x,k)=>(x-mx)*(ys[k]-my)));
      return {value:sx>0&&sy>0?Math.max(-1,Math.min(1,covariance/(sx*sy))):null,count:common.length};
    }));
    return correlations;
  },[data.fx]);

  const momentumRows=pairSeries.map(row=>({
    ...row,movePercent:row.momentum===null?null:row.momentum*100,
    dailyPercent:row.dailyMove===null?null:row.dailyMove*100,
    volatilityPercent:row.volatility===null?null:row.volatility*100,
    reading:row.momentum===null?"Insufficient history":row.momentum>.0025?"KES weaker":row.momentum<-.0025?"KES firmer":"Little changed"
  }));
  const ranked=[...momentumRows].filter(row=>row.momentum!==null).sort((a,b)=>b.momentum!-a.momentum!);
  const mostVolatile=[...momentumRows].filter(row=>row.volatility!==null).sort((a,b)=>b.volatility!-a.volatility!)[0];
  const latestDates=pairSeries.map(row=>row.latest?.date).filter((date):date is string=>Boolean(date));
  const chartRows=momentumRows.filter(row=>row.momentum!==null).map(row=>({pair:row.pair,move:row.movePercent!,volatility:row.volatilityPercent??0,reading:row.reading}));
  const chartCorrelation=momentumRows.filter(row=>row.movePercent!==null&&row.volatilityPercent!==null).map(row=>({pair:row.pair,x:row.volatilityPercent!,y:row.movePercent!}));
  const averageAbsCorrelation=(()=>{
    const values=[correlationRows[0]?.[1]?.value,correlationRows[0]?.[2]?.value,correlationRows[1]?.[2]?.value].filter((value):value is number=>value!==null&&value!==undefined);
    return values.length?mean(values.map(Math.abs)):null;
  })();
  const horizonLabel=horizon+"-observation";
  const formatMove=(value:number|null)=>value===null?"—":(value>0?"+":"")+pct(value,3);
  const correlationClass=(value:number|null)=>value===null?"correlation-missing":value>=.7?"correlation-high":value>=.3?"correlation-mid":value<=-.7?"correlation-negative":"correlation-low";

  return <div className="workspace-stack market-intelligence-workspace">
    <Panel title="Cross-currency momentum" note="Rank recent quote movement across the tracked pairs; a rising quote means the KES is weaker">
      <div className="intelligence-controls">
        <div><span className="intelligence-control-label">Comparison horizon</span><div className="market-range-group" role="group" aria-label="Momentum horizon">
          {windowOptions.map(value=><button type="button" key={value} className={horizon===value?"active":""} aria-pressed={horizon===value} onClick={()=>setHorizon(value)}>{value} obs.</button>)}
        </div></div>
        <div className="intelligence-coverage"><span>Latest observations</span><strong>{latestDates.length?latestDates.sort().at(-1):"—"}</strong><small>Window shown in trading observations, not calendar days</small></div>
      </div>
      <div className="intelligence-kpis">
        <Metric label="Largest KES weakening" value={ranked.length?ranked[0].pair:"—"} note={ranked.length?formatMove(ranked[0].momentum)+" over "+horizonLabel:"Insufficient history"}/>
        <Metric label="Largest KES strengthening" value={ranked.length?ranked.at(-1)!.pair:"—"} note={ranked.length?formatMove(ranked.at(-1)!.momentum)+" over "+horizonLabel:"Insufficient history"}/>
        <Metric label="Most volatile pair" value={mostVolatile?.pair||"—"} note={mostVolatile?.volatility===null||!mostVolatile?"Insufficient history":pct(mostVolatile.volatility,2)+" annualised"}/>
        <Metric label="Average absolute correlation" value={averageAbsCorrelation===null?"—":averageAbsCorrelation.toFixed(3)} note="Pairwise daily returns · aligned dates"/>
      </div>
      <div className="intelligence-ranking-table">
        <Table headers={["Currency pair","Latest quote","Daily move",horizon+"-observation move","Annualised volatility","Reading"]} rows={momentumRows.map(row=>[
          row.pair,row.latest?.value.toFixed(4)||"—",formatMove(row.dailyMove),formatMove(row.momentum),row.volatility===null?"—":pct(row.volatility,2),row.reading
        ])}/>
      </div>
      <p className="panel-note">Movement and volatility are descriptive statistics calculated from stored CBK observations. The reading is not a buy/sell signal or a forecast.</p>
    </Panel>

    <div className="dashboard-grid intelligence-chart-grid">
      <Panel title={horizon+"-observation relative movement"} note="Positive bars mean more KES are required per foreign-currency unit">
        {chartRows.length?<ChartFrame height={270} className="intelligence-momentum-chart"><ResponsiveContainer><BarChart data={chartRows} margin={{top:12,right:10,bottom:6,left:4}}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7edf2"/>
          <XAxis dataKey="pair" tick={{fontSize:10,fill:"#8291a0"}}/>
          <YAxis tick={{fontSize:10,fill:"#8291a0"}} unit="%" width={52}/>
          <ReferenceLine y={0} stroke="#9aa6b2"/>
          <Tooltip contentStyle={{borderRadius:9,border:"1px solid #e4eaf0",fontSize:11,boxShadow:"0 8px 24px rgba(20,43,67,.08)"}} formatter={(value:unknown)=>pct(Number(value)/100,3)} labelFormatter={label=>"Currency pair: "+String(label)}/>
          <Bar dataKey="move" name="Quote movement" radius={[4,4,0,0]}>{chartRows.map(row=><Cell key={row.pair} fill={row.move>=0?"#d5a43b":"#087f8c"}/>)}</Bar>
        </BarChart></ResponsiveContainer></ChartFrame>:<NoData message="No currency pair has enough observations for the selected comparison window."/>}
      </Panel>

      <Panel title="Return and risk positioning" note="Each point is one currency pair; compare momentum with annualised volatility">
        {chartCorrelation.length?<ChartFrame height={270} className="intelligence-scatter-chart"><ResponsiveContainer><ScatterChart margin={{top:12,right:18,bottom:8,left:8}}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e7edf2"/>
          <XAxis type="number" dataKey="x" name="Annualised volatility" unit="%" tick={{fontSize:9,fill:"#8291a0"}}/>
          <YAxis type="number" dataKey="y" name="Momentum" unit="%" tick={{fontSize:9,fill:"#8291a0"}}/>
          <ReferenceLine x={mean(chartCorrelation.map(row=>row.x))} stroke="#9aa6b2" strokeDasharray="3 3"/>
          <ReferenceLine y={0} stroke="#9aa6b2"/>
          <Tooltip cursor={{strokeDasharray:"3 3"}} formatter={(value,name)=>[Number(value).toFixed(2)+"%",String(name)]} labelFormatter={(_,payload)=>payload?.[0]?.payload?.pair||"Pair"}/>
          <Scatter name="Currency pairs" data={chartCorrelation} fill="#356bb3"/>
        </ScatterChart></ResponsiveContainer></ChartFrame>:<NoData message="Volatility and momentum positioning will appear once sufficient observations are available."/>}
      </Panel>
    </div>

    <Panel title="Daily-return correlation" note="Pearson correlation calculated only on dates observed for both currency pairs">
      <div className="correlation-legend"><span><i className="corr-dot high"/> Strong positive</span><span><i className="corr-dot mid"/> Moderate positive</span><span><i className="corr-dot negative"/> Strong negative</span><span><i className="corr-dot low"/> Weak / mixed</span></div>
      <div className="correlation-matrix-wrap"><table className="correlation-matrix">
        <thead><tr><th>Pair</th>{PAIRS.map(pair=><th key={pair}>{pair}</th>)}</tr></thead>
        <tbody>{PAIRS.map((pair,i)=><tr key={pair}><th>{pair}</th>{PAIRS.map((other,j)=>{
          const cell=correlationRows[i][j];
          return <td key={other}><div className={"correlation-cell "+correlationClass(cell.value)}>{cell.value===null?"—":cell.value.toFixed(2)}</div><small>{cell.count} dates</small></td>;
        })}</tr>)}</tbody>
      </table></div>
      <p className="panel-note">A positive correlation means the two KES exchange-rate quotes tended to move in the same direction on shared observation dates. Correlation is not causation and does not by itself imply diversification benefit.</p>
    </Panel>
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
  const curveRates=Object.fromEntries(ordered.map(row=>[row.tenor_days,row.rate])) as Record<number,number>;
  const slopes=yieldCurveSlopes(curveRates);
  const shape=latestCurve.length===TENORS.length
    ?classifyYieldCurve(curveRates).replace("UPWARD SLOPING","Upward / normal").replace("DOWNWARD SLOPING","Downward / inverted").replace("MIXED / HUMPED","Mixed / humped").replace("INSUFFICIENT DATA","Not enough matched tenors")
    :"Partial curve · "+latestCurve.length+" of "+TENORS.length+" matched tenors";
  const interpolate=(target:number):number|null=>ordered.length>=2&&target>=91&&target<=364?interpolateYield(target,curveRates):null;
  const [startDays,setStartDays]=useState("91"),[endDays,setEndDays]=useState("364");
  const start=Number(startDays),end=Number(endDays),r1=interpolate(start),r2=interpolate(end);
  const t1=start/365,t2=end/365;
  const forwardRate=r1!==null&&r2!==null&&end>start
    ? simpleForwardRate(r1,r2,start,end)
    : null;
  const slopeRows=[
    {segment:"91 to 182 days",value:slopes["91_to_182"]??null},
    {segment:"182 to 364 days",value:slopes["182_to_364"]??null},
    {segment:"91 to 364 days",value:slopes["91_to_364"]??null}
  ];
  const interpolationDays=[120,150,210,270,300];
  return <div className="workspace-stack">
    <Panel title="Latest recorded auction curve" note={latestDate||"No matched auction date"}>
      <div className="metric-grid">
        {TENORS.map(tenor=>{const row=latestCurve.find(x=>x.tenor_days===tenor);return <Metric key={tenor} label={tenor+"-day spot yield"} value={row?pct(row.rate,4):"—"} note={row?.issue_number||"No observation for this auction"}/>})}
        <Metric label="364s–91s spread" value={spread===null?"—":pp(spread,3)} note={shape}/>
      </div>
      {curve.length>=2?<ChartFrame height={300}><ResponsiveContainer><LineChart data={curve}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7edf2"/><XAxis dataKey="tenor" tick={{fontSize:11,fill:"#8291a0"}} label={{value:"Tenor (days)",position:"insideBottom",offset:-3,fontSize:10}}/><YAxis tick={{fontSize:10,fill:"#8291a0"}} unit="%"/><ChartTooltip/><Line dataKey="yield" name="Auction yield" stroke="#356bb3" strokeWidth={2.5} dot={{r:5,fill:"#356bb3"}}/></LineChart></ResponsiveContainer></ChartFrame>:<NoData message="The latest auction does not contain two or more tenors on the same date. No missing observations have been estimated."/>}
      <div className="panel-note">Only observed tenors from the same auction date are plotted. Missing tenors are left missing; the curve never combines separate auction dates.</div>
      <div className="yield-curve-slope-table">
        <Table headers={["Observed segment","Yield difference","Reading"]} rows={slopeRows.map(row=>[
          row.segment,row.value===null?"Not available":pp(row.value,3),row.value===null?"Both tenors required":row.value>0?"Longer tenor pays more":row.value<0?"Longer tenor pays less":"No difference"
        ])}/>
      </div>
    </Panel>
    <Panel title="Interpolated spot rates" note="Piecewise linear interpolation between observed tenors, limited to the actual supported maturity range">
      <Table headers={["Model maturity","Interpolated spot yield","Method"]} rows={interpolationDays.map(day=>{
        const value=interpolate(day);
        return [day+" days",value===null?"Not available":pct(value,4),value===null?"Outside observed support":"Linear between adjacent observed tenors"];
      })}/>
      <p className="panel-note">These intermediate maturities are model estimates, not separate CBK auction observations. Values are not extrapolated outside the published 91–364 day range.</p>
    </Panel>
    <Panel title="Implied forward rate" note="Annualised simple forward yield derived using the 365-day Treasury bill investment-yield convention">
      <div className="control-row">
        <label className="field"><span>Forward period starts (days)</span><select className="search" value={startDays} onChange={e=>setStartDays(e.target.value)}>{[91,120,150,182,210,270].map(x=><option key={x} value={x}>{x} days</option>)}</select></label>
        <label className="field"><span>Forward period ends (days)</span><select className="search" value={endDays} onChange={e=>setEndDays(e.target.value)}>{[182,210,270,300,364].map(x=><option key={x} value={x}>{x} days</option>)}</select></label>
      </div>
      <div className="metric-grid"><Metric label="Implied simple forward rate" value={forwardRate===null?"—":pct(forwardRate,4)} note={forwardRate===null?"Choose an increasing maturity pair with available spot rates":"From day "+start+" to day "+end}/><Metric label="Short spot rate" value={r1===null?"—":pct(r1,4)}/><Metric label="Long spot rate" value={r2===null?"—":pct(r2,4)}/></div>
      <p className="panel-note">This is an implied rate from two modelled spot maturities, not a rate quoted by CBK or a forecast of future policy rates.</p>
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
  const price=valid?treasuryBillPrice(capital,annualRate,term):0;
  const discount=valid?capital-price:0;
  const investmentReturn=valid&&price>0?discount/price:0;
  const annualised=valid&&term>0?investmentReturn*365/term:0;
  const chart=rows.map(row=>({date:row.date,yield:row.rate*100}));
  const latestDate=data.bills.reduce((latest,row)=>!latest||row.date>latest?row.date:latest,"");
  const latestAuction=data.bills.filter(row=>row.date===latestDate).sort((a,b)=>a.tenor_days-b.tenor_days);
  const comparisons=TENORS.map(days=>{
    const row=latestAuction.find(item=>item.tenor_days===days);
    const purchase=row&&capital>0?treasuryBillPrice(capital,row.rate,days):null;
    return {days,row,purchase,discount:purchase===null?null:capital-purchase};
  });
  return <div className="workspace-stack treasury-workspace">
    <Panel title="Auction history by tenor" note="Choose one Treasury bill maturity; published auction observations only">
      <div className="treasury-filter-row">
        <label className="field"><span>Bill maturity</span><select className="search" value={tenor} onChange={e=>setTenor(e.target.value)}>{TENORS.map(t=><option key={t} value={t}>{t}-day Treasury bill</option>)}</select></label>
      </div>
      <div className="treasury-kpi-grid">
        <Metric label="Latest market-weighted yield" value={rates.length?pct(rates.at(-1)!,4):"—"} note={rows.at(-1)?.date||"No auction record"}/>
        <Metric label="Historical average" value={rates.length?pct(mean(rates),4):"—"} note={rows.length+" observations"}/>
        <Metric label="Observed range" value={rates.length?((Math.max(...rates)-Math.min(...rates))*100).toFixed(3)+" pp":"—"} note="High less low in stored history"/>
      </div>
      {chart.length>=2?<ChartFrame height={270} className="treasury-chart"><ResponsiveContainer><LineChart data={chart}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7edf2"/><XAxis dataKey="date" minTickGap={25} tick={{fontSize:10,fill:"#8291a0"}}/><YAxis tick={{fontSize:10,fill:"#8291a0"}} unit="%"/><Tooltip formatter={(value)=>pct(Number(value)/100,4)} labelFormatter={label=>"Auction date: "+String(label)} contentStyle={{borderRadius:9,border:"1px solid #e4eaf0",fontSize:11,boxShadow:"0 8px 24px rgba(20,43,67,.08)"}}/><Line dataKey="yield" name="Accepted yield" stroke="#d5a43b" strokeWidth={2.2} dot={false}/></LineChart></ResponsiveContainer></ChartFrame>:<NoData message="More than one auction observation is needed to draw a history for this tenor."/>}
      <div className="treasury-history-table"><Table headers={["Auction date","Accepted yield","Issue number","Publisher"]} rows={[...rows].reverse().map(row=>[row.date,pct(row.rate,4),row.issue_number||"—",row.source])}/></div>
    </Panel>
    <Panel title="Treasury bill purchase-price calculator" note="Investment-yield convention from the retained pricing engine; 365-day basis">
      <div className="metric-grid treasury-calculator-fields"><Field label="Face value (KES)" value={face} onChange={setFace} min="1"/><Field label="Annual investment yield (%)" value={yieldRate} onChange={setYieldRate} min="0" max="100"/><Field label="Days to maturity" value={days} onChange={setDays} min="1" max="364"/></div>
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
  const valid=[f,c,y,n,t].every(Number.isFinite)&&f>0&&c>=0&&c<=1&&y>-1&&y<=1&&t>0&&t<=100&&[1,2,4].includes(n)&&Math.round(t*n)>=1;
  const marketPriceValid=Number.isFinite(observedPrice)&&observedPrice>0;
  const shockValid=Number.isFinite(dy)&&Math.abs(Number(shockBps))<=5000;
  const periods=valid?Math.max(1,Math.round(t*n)):0;
  const model=valid?bondMetrics(f,c,y,t,n):null;
  const price=model?.price||0,macaulay=model?.macaulay_duration||0,modified=model?.modified_duration||0,convexity=model?.convexity||0;
  const flows=valid?bondCashFlows(f,c,t,n).map(row=>({...row,pv:row.cash_flow/Math.pow(1+y/n,row.period)})):[];
  const priceAt=(yieldRate:number)=>bondPrice(f,c,yieldRate,t,n);
  const minPrice=valid?priceAt(2.0):0,maxPrice=valid?priceAt(-.99):0;
  const ytmValid=valid&&marketPriceValid&&observedPrice>=minPrice&&observedPrice<=maxPrice;
  const impliedYtm=ytmValid?bondYtm(f,c,observedPrice,t,n):null;
  const sensitivity=valid&&shockValid?bondPriceSensitivity(f,c,y,t,dy,n):null;
  const estimatedChange=sensitivity?sensitivity.estimated_change_percent/100:0;
  const shockedPrice=sensitivity?.estimated_price||0;
  const sensitivityValid=!!sensitivity&&Number.isFinite(shockedPrice)&&shockedPrice>0;
  return <div className="workspace-stack">
    <Panel title="Fixed-rate bond valuation" note="Periodic coupon discounting with the original annual, semi-annual and quarterly payment frequencies">
      <div className="metric-grid"><Field label="Face value (KES)" value={face} onChange={setFace} min="1"/><Field label="Annual coupon rate (%)" value={coupon} onChange={setCoupon} min="0" max="100"/><Field label="Yield to maturity (%)" value={ytm} onChange={setYtm} min="-99" max="100"/><Field label="Years to maturity" value={years} onChange={setYears} min="0.01" max="100"/><label className="field"><span>Payments per year</span><select className="search" value={frequency} onChange={e=>setFrequency(e.target.value)}><option value="1">Annual</option><option value="2">Semi-annual</option><option value="4">Quarterly</option></select></label></div>
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
      {valid?<Table headers={["Period","Time (years)","Coupon / redemption cash flow","Present value"]} rows={flows.map(row=>[row.period,row.time.toFixed(2),money(row.cash_flow),money(row.pv)])}/>:<NoData message="Valid bond inputs are required to calculate the cash-flow schedule."/>}
    </Panel>

    <Panel title="Bond price across yield scenarios" note="Full revaluation of the model cash flows at a range of annual yields">
      {valid?<ChartFrame height={260} className="bond-price-chart"><ResponsiveContainer><LineChart data={Array.from({length:26},(_,i)=>{const yieldRate=i/100;return {yield:(yieldRate*100).toFixed(1),price:bondPrice(f,c,yieldRate,t,n)};})} margin={{top:10,right:12,bottom:4,left:2}}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7edf2"/>
        <XAxis dataKey="yield" tick={{fontSize:10,fill:"#8291a0"}} unit="%"/>
        <YAxis tick={{fontSize:10,fill:"#8291a0"}} width={68} tickFormatter={value=>money(Number(value))}/>
        <Tooltip formatter={(value)=>money(Number(value))} labelFormatter={label=>"Yield to maturity: "+String(label)+"%"} contentStyle={{borderRadius:9,border:"1px solid #e4eaf0",fontSize:11,boxShadow:"0 8px 24px rgba(20,43,67,.08)"}}/>
        <ReferenceLine x={(y*100).toFixed(1)} stroke="#d5a43b" strokeDasharray="4 4" label={{value:"Current YTM",position:"insideTopRight",fill:"#a27a24",fontSize:10}}/>
        <Line dataKey="price" name="Bond price" stroke="#356bb3" strokeWidth={2.4} dot={false} activeDot={{r:4}}/>
      </LineChart></ResponsiveContainer></ChartFrame>:<NoData message="Valid bond terms are required before drawing the price–yield relationship."/>}
      <p className="panel-note">The graph shows the inverse price–yield relationship for this bond's coupon and maturity. It reprices the cash flows at each point rather than applying the duration approximation.</p>
    </Panel>
    <Panel title="Coupon and redemption profile" note="Cash-flow size by payment period, with principal redemption included at maturity">
      {valid?<ChartFrame height={240} className="bond-cashflow-chart"><ResponsiveContainer><BarChart data={flows} margin={{top:8,right:12,bottom:4,left:2}}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7edf2"/>
        <XAxis dataKey="period" tick={{fontSize:10,fill:"#8291a0"}}/>
        <YAxis tick={{fontSize:10,fill:"#8291a0"}} width={68} tickFormatter={value=>Number(value).toLocaleString("en-KE",{maximumFractionDigits:0})}/>
        <Tooltip formatter={(value)=>money(Number(value))} labelFormatter={label=>"Payment period: "+String(label)} contentStyle={{borderRadius:9,border:"1px solid #e4eaf0",fontSize:11,boxShadow:"0 8px 24px rgba(20,43,67,.08)"}}/>
        <Bar dataKey="cash_flow" name="Contractual cash flow" radius={[4,4,0,0]}>
          {flows.map((row,index)=><Cell key={"cashflow-"+row.period} fill={index===flows.length-1?"#d5a43b":"#087f8c"}/>)}
        </Bar>
      </BarChart></ResponsiveContainer></ChartFrame>:<NoData message="Enter valid bond terms to generate the payment profile."/>}
    </Panel>
  </div>;
}

function OptionsGreeks(){
  const [spot,setSpot]=useState("100"),[strike,setStrike]=useState("100"),[maturity,setMaturity]=useState("1"),[riskFree,setRiskFree]=useState("13"),[volatility,setVolatility]=useState("20"),[kind,setKind]=useState("Call");
  const S=Number(spot),K=Number(strike),T=Number(maturity),r=Number(riskFree)/100,sigma=Number(volatility)/100;
  const valid=[S,K,T,sigma,r].every(Number.isFinite)&&S>0&&K>0&&T>0&&T<=100&&sigma>0&&sigma<=5&&r>=-1&&r<=1;
  const greeks=valid?blackScholes({spot:S,strike:K,time:T,rate:r,volatility:sigma,type:kind as "Call"|"Put"}):null;
  const price=greeks?.price||0,delta=greeks?.delta||0,gamma=greeks?.gamma||0,vega=greeks?.vega||0,theta=greeks?.theta||0,rho=greeks?.rho||0;
  return <div className="workspace-stack">
    <Panel title="Black–Scholes model" note="European option; continuous risk-free rate, no dividends or transaction costs" action={<select className="search" aria-label="Option type" value={kind} onChange={e=>setKind(e.target.value)}><option>Call</option><option>Put</option></select>}>
      <div className="metric-grid"><Field label="Underlying price" value={spot} onChange={setSpot} min="0.01"/><Field label="Strike price" value={strike} onChange={setStrike} min="0.01"/><Field label="Time to expiry (years)" value={maturity} onChange={setMaturity} min="0.001" max="100"/><Field label="Risk-free rate (%)" value={riskFree} onChange={setRiskFree} min="-100" max="100"/><Field label="Volatility (%)" value={volatility} onChange={setVolatility} min="0.01" max="500"/></div>
      {valid?<div className="metric-grid"><Metric label={kind+" model value"} value={price.toFixed(6)}/><Metric label="Delta" value={delta.toFixed(5)}/><Metric label="Gamma" value={gamma.toFixed(6)}/><Metric label="Vega / 1 vol point" value={vega.toFixed(5)}/><Metric label="Theta / day" value={theta.toFixed(6)}/><Metric label="Rho / 1 rate point" value={rho.toFixed(5)}/></div>:<NoData message="Enter positive spot and strike, time to expiry up to 100 years, volatility above 0% and no greater than 500%, and a risk-free rate from −100% to 100%."/>}
    </Panel>
    <Panel title="Model assumptions" note="Read before comparing model value with an observed market option price">
      <Table headers={["Input","Assumption"]} rows={[["Exercise","European, exercise only at expiry"],["Underlying","No dividends or carry adjustment"],["Volatility","Constant over the option life"],["Interest rate","Constant continuously compounded risk-free rate"],["Market frictions","No transaction costs, bid–ask spread or liquidity adjustment"]]}/>
    </Panel>

    <Panel title="Option value versus underlying price" note="Reprices the selected call or put while other Black–Scholes inputs remain fixed">
      {valid?<ChartFrame height={280}><ResponsiveContainer><LineChart data={Array.from({length:21},(_,i)=>{const spotValue=S*(.6+i*.04);const result=blackScholes({spot:spotValue,strike:K,time:T,rate:r,volatility:sigma,type:kind as "Call"|"Put"});return {spot:spotValue.toFixed(2),optionValue:result.price,intrinsic:Math.max(kind==="Call"?spotValue-K:K-spotValue,0)};})}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7edf2"/>
        <XAxis dataKey="spot" tick={{fontSize:10,fill:"#8291a0"}} label={{value:"Underlying price",position:"insideBottom",offset:-3,fontSize:10}}/>
        <YAxis tick={{fontSize:10,fill:"#8291a0"}} width={55}/>
        <ChartTooltip/>
        <Line dataKey="optionValue" name={kind+" model value"} stroke="#8064b2" strokeWidth={2.4} dot={false}/>
        <Line dataKey="intrinsic" name="Intrinsic value" stroke="#9aa6b2" strokeDasharray="5 4" dot={false}/>
      </LineChart></ResponsiveContainer></ChartFrame>:<NoData message="Valid option inputs are required to plot option value against the underlying."/>}
    </Panel>
    <Panel title="Delta and gamma by underlying price" note="Sensitivity profile around the current spot; gamma is displayed on a separate chart scale">
      {valid?<ChartFrame height={260}><ResponsiveContainer><LineChart data={Array.from({length:21},(_,i)=>{const spotValue=S*(.6+i*.04);const result=blackScholes({spot:spotValue,strike:K,time:T,rate:r,volatility:sigma,type:kind as "Call"|"Put"});return {spot:spotValue.toFixed(2),delta:result.delta,gamma:result.gamma};})}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7edf2"/>
        <XAxis dataKey="spot" tick={{fontSize:10,fill:"#8291a0"}}/>
        <YAxis yAxisId="delta" domain={[-1,1]} tick={{fontSize:10,fill:"#8291a0"}}/>
        <YAxis yAxisId="gamma" orientation="right" tick={{fontSize:10,fill:"#8291a0"}}/>
        <ChartTooltip/>
        <Line yAxisId="delta" dataKey="delta" name="Delta" stroke="#087f8c" strokeWidth={2} dot={false}/>
        <Line yAxisId="gamma" dataKey="gamma" name="Gamma" stroke="#d5a43b" strokeWidth={2} dot={false}/>
      </LineChart></ResponsiveContainer></ChartFrame>:<NoData message="Valid option inputs are required to plot the Greeks."/>}
    </Panel>
  </div>;
}

function RiskAnalysis({data}:{data:MarketPayload}){
  const [pair,setPair]=useState("USD/KES"),[capital,setCapital]=useState("1000000"),[confidence,setConfidence]=useState("95"),[riskFree,setRiskFree]=useState("8.75");
  const {rows,values,rets}=seriesFor(data.fx,pair);
  const confidenceValue=Number(confidence)/100,exposure=Number(capital),rf=Number(riskFree)/100;
  const valid=rets.length>=2&&Number.isFinite(exposure)&&exposure>0&&Number.isFinite(rf);
  const historical=valid?historicalVaR(rets,exposure,confidenceValue):0;
  const parametric=valid?parametricVaR(rets,exposure,confidenceValue):0;
  const es=valid?expectedShortfall(rets,exposure,confidenceValue):0;
  const volatility=valid?annualizedVolatility(rets):0;
  const sharpe=valid?sharpeRatio(rets,rf):0;
  const sortino=valid?sortinoRatio(rets):0;
  const lower=rets.length?Math.min(...rets):0,upper=rets.length?Math.max(...rets):0;
  const width=upper>lower?(upper-lower)/12:Math.max(Math.abs(lower)*0.1,0.000001);
  const bins=Array.from({length:12},(_,i)=>{
    const start=lower+i*width,end=i===11?upper:lower+(i+1)*width;
    return {label:(start*100).toFixed(2)+"% to "+(end*100).toFixed(2)+"%",count:0};
  });
  for(const value of rets){const idx=Math.max(0,Math.min(bins.length-1,Math.floor((value-lower)/width)));bins[idx].count++;}
  return <div className="workspace-stack">
    <Panel title="Historical FX risk" note="Loss estimates are based on the selected pair's observed daily percentage changes">
      <div className="control-row"><label className="field"><span>Currency pair</span><select className="search" value={pair} onChange={e=>setPair(e.target.value)}>{PAIRS.map(x=><option key={x}>{x}</option>)}</select></label><Field label="Exposure value (KES)" value={capital} onChange={setCapital} min="1"/><Field label="Annual risk-free rate (%)" value={riskFree} onChange={setRiskFree} min="0" max="100"/><label className="field"><span>Confidence level</span><select className="search" value={confidence} onChange={e=>setConfidence(e.target.value)}><option value="90">90%</option><option value="95">95%</option><option value="99">99%</option></select></label></div>
      <div className="metric-grid"><Metric label={"Historical VaR · "+confidence+"%"} value={valid?money(historical):"—"} note="Empirical lower-tail estimate"/><Metric label={"Parametric VaR · "+confidence+"%"} value={valid?money(parametric):"—"} note="Normal approximation"/><Metric label="Expected shortfall" value={valid?money(es):"—"} note="Mean of empirical tail losses"/><Metric label="Annualised volatility" value={valid?pct(volatility):"—"} note="Sample standard deviation × √252"/><Metric label="Sharpe ratio" value={valid?sharpe.toFixed(3):"—"} note="Uses the annual risk-free input"/><Metric label="Sortino ratio" value={valid?sortino.toFixed(3):"—"} note="Zero daily target return"/></div>
    </Panel>
    <Panel title="Daily return distribution" note={"Observed returns for "+pair+"; labels show actual sample-return intervals"}>
      {rets.length>=2?<ChartFrame height={280}><ResponsiveContainer><BarChart data={bins}><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7edf2"/><XAxis dataKey="label" tick={{fontSize:10,fill:"#8291a0"}}/><YAxis tick={{fontSize:10,fill:"#8291a0"}}/><ChartTooltip/><Bar dataKey="count" name="Observations" fill="#c18a35" radius={[3,3,0,0]}/></BarChart></ResponsiveContainer></ChartFrame>:<NoData message="At least three valid prices are needed to estimate historical returns."/>}
      <p className="panel-note">Historical VaR and expected shortfall use the empirical return sample; parametric VaR uses a normal approximation. These estimates do not guarantee a maximum loss. The selected currency series is a market proxy, not a diversified portfolio return history.</p>
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
  const [kind,setKind]=useState("FX");
  const [pair,setPair]=useState("All");
  const [tenor,setTenor]=useState("All");
  const [from,setFrom]=useState("");
  const [to,setTo]=useState("");
  const [search,setSearch]=useState("");
  const [view,setView]=useState<"chart"|"records">("chart");

  const query=search.trim().toLowerCase();
  const fx=data.fx.filter(row=>
    (pair==="All"||row.instrument===pair)&&
    (!from||row.date>=from)&&(!to||row.date<=to)&&
    (!query||row.source.toLowerCase().includes(query)||row.date.includes(query)||row.instrument.toLowerCase().includes(query))
  ).sort((a,b)=>a.date.localeCompare(b.date));
  const bills=data.bills.filter(row=>
    (tenor==="All"||row.tenor_days===Number(tenor))&&
    (!from||row.date>=from)&&(!to||row.date<=to)&&
    (!query||row.source.toLowerCase().includes(query)||row.date.includes(query)||String(row.issue_number||"").toLowerCase().includes(query))
  ).sort((a,b)=>a.date.localeCompare(b.date));

  const fxChartRows=(()=>{
    const byDate=new Map<string,Record<string,number|string|null>>();
    for(const row of fx){
      if(!byDate.has(row.date))byDate.set(row.date,{date:row.date});
      const entry=byDate.get(row.date)!;
      entry[row.instrument.replace("/","_")]=row.value;
    }
    return [...byDate.values()];
  })();
  const billChartRows=(()=>{
    const byDate=new Map<string,Record<string,number|string|null>>();
    for(const row of bills){
      if(!byDate.has(row.date))byDate.set(row.date,{date:row.date});
      const entry=byDate.get(row.date)!;
      entry["TBILL_"+row.tenor_days]=row.rate*100;
    }
    return [...byDate.values()];
  })();

  const count=kind==="FX"?fx.length:bills.length;
  const dateRows=kind==="FX"?fx:bills;
  const firstDate=dateRows[0]?.date||"—";
  const lastDate=dateRows.at(-1)?.date||"—";
  const headers=kind==="FX"?["Date","Currency pair","KES per unit","Source"]:["Auction date","Tenor","Accepted yield","Issue number","Source"];
  const exportRows=kind==="FX"
    ?fx.map(row=>[row.date,row.instrument,row.value,row.source])
    :bills.map(row=>[row.date,row.tenor_days,row.rate,row.issue_number||"",row.source]);
  const visibleRows=[...exportRows].reverse().map(row=>
    kind==="FX"
      ?[row[0],row[1],Number(row[2]).toFixed(4),row[3]]
      :[row[0],row[1]+" days",pct(Number(row[2]),4),row[3],row[4]]
  );

  const clearFilters=()=>{
    setPair("All");setTenor("All");setFrom("");setTo("");setSearch("");
  };

  return <div className="workspace-stack explorer-workspace">
    <Panel title="Historical market explorer" note="Choose a dataset, narrow the observation window and inspect the results without leaving the filter area">
      <div className="explorer-filter-grid">
        <label className="field"><span>Dataset</span><select className="search" value={kind} onChange={event=>{setKind(event.target.value);setView("chart");}}><option>FX</option><option>Treasury bills</option></select></label>
        {kind==="FX"
          ?<label className="field"><span>Currency pair</span><select className="search" value={pair} onChange={event=>setPair(event.target.value)}><option value="All">All pairs</option>{PAIRS.map(value=><option key={value} value={value}>{value}</option>)}</select></label>
          :<label className="field"><span>Bill tenor</span><select className="search" value={tenor} onChange={event=>setTenor(event.target.value)}><option value="All">All tenors</option>{TENORS.map(value=><option key={value} value={value}>{value} days</option>)}</select></label>}
        <label className="field"><span>From date</span><input className="search" type="date" value={from} max={to||undefined} onChange={event=>setFrom(event.target.value)}/></label>
        <label className="field"><span>To date</span><input className="search" type="date" value={to} min={from||undefined} onChange={event=>setTo(event.target.value)}/></label>
        <label className="field"><span>Search date, pair or source</span><input className="search" value={search} onChange={event=>setSearch(event.target.value)} placeholder="Type to filter"/></label>
      </div>
      <div className="explorer-toolbar">
        <div className="explorer-result-meta">
          <strong>{count.toLocaleString("en-KE")} records</strong>
          <span>{firstDate} to {lastDate}</span>
          <button className="explorer-reset" onClick={clearFilters}>Reset filters</button>
        </div>
        <button className="primary-btn" disabled={count===0} onClick={()=>csvDownload(kind==="FX"?"KFA_FX_Historical_Observations.csv":"KFA_Treasury_Bill_Historical_Observations.csv",headers,exportRows)}>Export filtered CSV</button>
      </div>
      <div className="explorer-mobile-tabs" role="tablist" aria-label="Historical explorer view">
        <button type="button" role="tab" aria-selected={view==="chart"} className={view==="chart"?"active":""} onClick={()=>setView("chart")}>Chart</button>
        <button type="button" role="tab" aria-selected={view==="records"} className={view==="records"?"active":""} onClick={()=>setView("records")}>Records ({count})</button>
      </div>
    </Panel>

    <div className="explorer-results-grid">
      <div className={"explorer-result-panel explorer-chart-panel "+(view==="chart"?"selected":"")}>
        <Panel title={kind==="FX"?"Exchange-rate history":"Treasury bill yield history"} note={kind==="FX"?"KES per foreign-currency unit · daily CBK observations":"Accepted auction yield · annual percentage"}>
          {count===0
            ?<NoData message="No observations match these filters. Widen the date range or reset the filters."/>
            :kind==="FX"
              ?<ChartFrame height={300}><ResponsiveContainer><LineChart data={fxChartRows}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7edf2"/>
                <XAxis dataKey="date" minTickGap={25} tick={{fontSize:10,fill:"#8291a0"}}/>
                <YAxis tick={{fontSize:10,fill:"#8291a0"}} domain={["auto","auto"]}/>
                <ChartTooltip/>
                {(pair==="All"||pair==="USD/KES")&&<Line dataKey="USD_KES" name="USD/KES" stroke="#087f8c" strokeWidth={2} dot={false} connectNulls={false}/>}
                {(pair==="All"||pair==="GBP/KES")&&<Line dataKey="GBP_KES" name="GBP/KES" stroke="#356bb3" strokeWidth={2} dot={false} connectNulls={false}/>}
                {(pair==="All"||pair==="EUR/KES")&&<Line dataKey="EUR_KES" name="EUR/KES" stroke="#d5a43b" strokeWidth={2} dot={false} connectNulls={false}/>}
              </LineChart></ResponsiveContainer></ChartFrame>
              :<ChartFrame height={300}><ResponsiveContainer><LineChart data={billChartRows}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7edf2"/>
                <XAxis dataKey="date" minTickGap={25} tick={{fontSize:10,fill:"#8291a0"}}/>
                <YAxis tick={{fontSize:10,fill:"#8291a0"}} unit="%" domain={["auto","auto"]}/>
                <ChartTooltip/>
                {(tenor==="All"||tenor==="91")&&<Line dataKey="TBILL_91" name="91-day" stroke="#087f8c" strokeWidth={2} dot={false}/>}
                {(tenor==="All"||tenor==="182")&&<Line dataKey="TBILL_182" name="182-day" stroke="#356bb3" strokeWidth={2} dot={false}/>}
                {(tenor==="All"||tenor==="364")&&<Line dataKey="TBILL_364" name="364-day" stroke="#d5a43b" strokeWidth={2} dot={false}/>}
              </LineChart></ResponsiveContainer></ChartFrame>}
          <p className="panel-note">Missing dates remain gaps. The explorer does not forward-fill exchange rates or invent auction observations.</p>
        </Panel>
      </div>

      <div className={"explorer-result-panel explorer-records-panel "+(view==="records"?"selected":"")}>
        <Panel title="Observation records" note="Newest records first · scroll within this list to inspect older observations">
          {count===0
            ?<NoData message="There are no matching records to display."/>
            :<div className="explorer-table-wrap"><Table headers={headers} rows={visibleRows}/></div>}
        </Panel>
      </div>
    </div>
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
  const missingBillHistory=positions.some(row=>row.isTbill&&row.value>0&&(!row.latest||data.bills.filter(item=>item.tenor_days===row.tenor).length<2));
  const valid=positions.every(row=>Number.isFinite(row.value)&&row.value>=0&&Number.isFinite(row.expected)&&Number.isFinite(row.volatility)&&row.volatility>=0)&&
    Number.isFinite(Number(bondReturn))&&Number(bondReturn)>=-100&&Number(bondReturn)<=100&&
    Number.isFinite(Number(bondVol))&&Number(bondVol)>=0&&Number(bondVol)<=100&&
    Number.isFinite(Number(cashReturn))&&Number(cashReturn)>=-100&&Number(cashReturn)<=100&&
    Number.isFinite(Number(cashVol))&&Number(cashVol)>=0&&Number(cashVol)<=100&&!missingBillHistory;
  const active=valid?positions.filter(row=>row.value>0):[];
  const engine=active.length?portfolioMetrics(active.map(row=>({name:row.name,value:row.value,expected_return:row.expected,volatility:row.volatility}))):null;
  const total=engine?.total_value||0;
  const alloc=active.map((row,i)=>({...row,weight:engine?.allocation[i].weight||0,annualPnl:row.value*row.expected}));
  const expectedPnl=engine?.expected_annual_pnl||0;
  const expectedReturn=engine?.expected_return||0;
  const portfolioVolatility=engine?.volatility||0;
  const var95=engine?.parametric_var_95||0;
  const var99=2.32635*portfolioVolatility*total/Math.sqrt(252);
  const largest=alloc.reduce((best,row)=>!best||row.weight>best.weight?row:best,null as typeof alloc[number]|null);
  const hhi=engine?.concentration_hhi||0;
  const diversification=engine?.diversification_score||0;
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
      {!valid||total<=0?<NoData message={missingBillHistory?"A Treasury bill position needs a latest CBK auction yield and at least two historical auctions for its risk estimate. Reduce that position to zero or restore the missing auction history.":"Enter finite, non-negative KES position values, valid return and volatility assumptions, and at least one positive position value."}/>:
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

    <Panel title="Expected return and risk contribution" note="Per-position annual expected P&L beside its independent-position volatility contribution">
      {alloc.length?<ChartFrame height={290}><ResponsiveContainer><BarChart data={alloc.map(row=>({position:row.name,pnl:row.annualPnl,weightedRisk:row.weight*row.volatility*100}))} layout="vertical">
        <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e7edf2"/>
        <XAxis type="number" tick={{fontSize:10,fill:"#8291a0"}}/>
        <YAxis dataKey="position" type="category" width={145} tick={{fontSize:10,fill:"#8291a0"}}/>
        <ChartTooltip/>
        <Bar dataKey="pnl" name="Expected annual P&L (KES)" fill="#16835d" radius={[0,4,4,0]}/>
      </BarChart></ResponsiveContainer></ChartFrame>:<NoData message="Add at least one positive-value position to see its contribution."/>}
      <Table headers={["Position","Weight","Weighted volatility contribution"]} rows={alloc.map(row=>[row.name,pct(row.weight),pct(row.weight*row.volatility)])}/>
      <p className="panel-note">Expected return and volatility assumptions are not the same measure. The chart shows expected KES P&L; the table separately reports each position's weighted volatility contribution.</p>
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

function FinancialReports({data}:{data:MarketPayload}){
  const generated=new Date().toLocaleString("en-KE");
  const [reporting,setReporting]=useState(false),[reportError,setReportError]=useState("");
  const downloadExcelReport=async()=>{
    setReporting(true);setReportError("");
    try{
      const response=await fetch("/api/report",{cache:"no-store"});
      if(!response.ok){
        let message="The formatted Excel report could not be generated.";
        try{const payload=await response.json();message=payload.error||message;}catch{}
        throw new Error(message);
      }
      const blob=await response.blob();
      const url=URL.createObjectURL(blob),anchor=document.createElement("a");
      anchor.href=url;anchor.download="Kenya_Financial_Analytics_Market_Report.xlsx";
      document.body.appendChild(anchor);anchor.click();anchor.remove();
      window.setTimeout(()=>URL.revokeObjectURL(url),1000);
    }catch(error){
      setReportError(error instanceof Error?error.message:"The report download failed. Please retry.");
    }finally{setReporting(false);}
  };
  const fx=PAIRS.map(pair=>{const {rows,values,rets}=seriesFor(data.fx,pair);return {pair,rows,latest:values.at(-1),change:values.length>1?values.at(-1)!/values[0]-1:0,vol:stdev(rets)*Math.sqrt(252)};});
  const dates=data.bills.map(x=>x.date).sort(),latestDate=dates.at(-1)||"";
  const latestBills=data.bills.filter(row=>row.date===latestDate).sort((a,b)=>a.tenor_days-b.tenor_days);
  const summaryCsvRows=[
    ...fx.map(x=>["FX",x.pair,x.rows.at(-1)?.date||"",x.latest??"",x.change,x.vol,x.rows.length,x.rows.at(-1)?.source||"",x.rows.at(-1)?.source_url||""]),
    ...latestBills.map(row=>["Treasury bill",row.tenor_days+" days",row.date,row.rate,"","",data.bills.filter(x=>x.tenor_days===row.tenor_days).length,row.source,row.source_url||""])
  ];
  const previousFxRate=new Map<string,number>();
  const fxHistoryRows=[...data.fx].sort((a,b)=>a.date.localeCompare(b.date)||a.instrument.localeCompare(b.instrument)).map(row=>{
    const previous=previousFxRate.get(row.instrument);
    const dailyChange=previous!==undefined&&previous!==0?row.value/previous-1:"";
    previousFxRate.set(row.instrument,row.value);
    return ["FX",row.date,row.instrument,"",row.value,"",dailyChange,"","","",row.source,row.source_url||""];
  });
  const billHistoryRows=data.bills.map(row=>["Treasury bill",row.date,"",row.tenor_days,row.rate,row.price??(100/(1+row.rate*row.tenor_days/365)),"",row.issue_number||"",row.amount_offered??"",row.amount_accepted??"",row.source,row.source_url||""]);
  const detailedCsvRows=[...fxHistoryRows,...billHistoryRows].sort((a,b)=>String(a[1]).localeCompare(String(b[1]))||String(a[0]).localeCompare(String(b[0]))||String(a[2]||a[3]).localeCompare(String(b[2]||b[3])));
  const summaryHeaders=["Record type","Instrument","Latest observation date","Latest rate / yield (decimal)","Cumulative FX change (decimal)","Annualised FX volatility (decimal)","Observations","Published source","Source URL"];
  const detailedHeaders=["Record type","Observation date","Currency pair","Tenor (days)","Rate / accepted yield (decimal)","Price per KES 100","Daily FX change (decimal)","Issue number","Amount offered (KES)","Amount accepted (KES)","Published source","Source URL"];
  return <div className="workspace-stack">
    <Panel title="Market research report" note={"Generated "+generated+" · Source: Central Bank of Kenya"}>
      <div className="metric-grid"><Metric label="FX observations" value={data.fx.length.toLocaleString("en-KE")}/><Metric label="Auction observations" value={data.bills.length.toLocaleString("en-KE")}/><Metric label="FX coverage" value={(data.fx.map(x=>x.date).sort()[0]||"—")+" to "+(data.health.latest_fx_observation||"—")}/><Metric label="Auction coverage" value={(dates[0]||"—")+" to "+(data.health.latest_bill_observation||"—")}/></div>
      <div className="panel-head"><div><div className="panel-title">Financial reporting exports</div><div className="panel-note">Formatted workbook for presentation; numeric CSV files for further analysis</div></div><div className="report-actions"><button className="primary-btn" onClick={()=>void downloadExcelReport()} disabled={reporting}>{reporting?"Preparing workbook…":"Download formatted Excel"}</button><button className="secondary-btn" onClick={()=>csvDownload("KFA_Executive_Summary.csv",summaryHeaders,summaryCsvRows)}>Executive summary CSV</button><button className="secondary-btn" onClick={()=>csvDownload("KFA_Full_Market_History.csv",detailedHeaders,detailedCsvRows)}>Full history CSV</button></div></div>
      {reportError&&<p className="report-error" role="alert">{reportError}</p>}
      <Table headers={["Pair","Latest date","Latest rate (KES / unit)","Cumulative change","Annualised volatility","Observations","Source"]} rows={fx.map(x=>[x.pair,x.rows.at(-1)?.date||"—",x.latest?.toFixed(4)||"—",pct(x.change),pct(x.vol),x.rows.length,x.rows.at(-1)?.source||"—"])}/>
    </Panel>
    <Panel title="Latest Treasury bill auction snapshot" note={latestDate||"No auction results in database"}>
      <Table headers={["Tenor","Auction date","Market-weighted yield","Issue number","Source"]} rows={latestBills.map(row=>[row.tenor_days+" days",row.date,pct(row.rate,4),row.issue_number||"—",row.source])}/>
    </Panel>
    <Panel title="Source and limitations" note="Report provenance">
      <p style={{fontSize:12,lineHeight:1.7,color:"var(--muted)",margin:0}}>Market values in this report are stored observations attributed to the Central Bank of Kenya. Data coverage may differ by instrument. No rates are estimated for missing dates or tenors. Volatility is calculated from observed daily FX changes and is not a forward-looking risk forecast.</p>
    </Panel>

    <Panel title="FX performance comparison" note="Each currency series is rebased to 100 at its own first stored observation">
      <ChartFrame height={300}><ResponsiveContainer><LineChart data={[...new Set(data.fx.map(x=>x.date))].sort().map(date=>{
        const result:Record<string,string|number|null>={date};
        for(const pair of PAIRS){
          const rows=pairRows(data.fx,pair);
          const first=rows[0]?.value;
          const current=rows.find(x=>x.date===date)?.value;
          result[pair.replace("/","_")]=first&&current!==undefined?current/first*100:null;
        }
        return result;
      })}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7edf2"/>
        <XAxis dataKey="date" minTickGap={25} tick={{fontSize:10,fill:"#8291a0"}}/>
        <YAxis tick={{fontSize:10,fill:"#8291a0"}} domain={["auto","auto"]}/>
        <ChartTooltip/>
        <Line dataKey="USD_KES" name="USD/KES index" stroke="#087f8c" strokeWidth={2} dot={false} connectNulls={false}/>
        <Line dataKey="GBP_KES" name="GBP/KES index" stroke="#356bb3" strokeWidth={2} dot={false} connectNulls={false}/>
        <Line dataKey="EUR_KES" name="EUR/KES index" stroke="#d5a43b" strokeWidth={2} dot={false} connectNulls={false}/>
      </LineChart></ResponsiveContainer></ChartFrame>
      <p className="panel-note">A value of 100 represents the first observation in each series. This allows relative movement to be compared without mixing the different currency quote levels.</p>
    </Panel>
    <Panel title="Treasury bill auction curve" note={"Matched rates from "+(latestDate||"the latest available auction date")}>
      {latestBills.length>=2?<ChartFrame height={250}><ResponsiveContainer><LineChart data={latestBills.map(row=>({tenor:row.tenor_days+" days",yield:row.rate*100}))}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7edf2"/>
        <XAxis dataKey="tenor" tick={{fontSize:10,fill:"#8291a0"}}/>
        <YAxis tick={{fontSize:10,fill:"#8291a0"}} unit="%"/>
        <ChartTooltip/>
        <Line dataKey="yield" name="Market-weighted auction yield" stroke="#d5a43b" strokeWidth={2.4} dot={{r:5}}/>
      </LineChart></ResponsiveContainer></ChartFrame>:<NoData message="At least two matched Treasury bill maturities are required to plot the auction curve."/>}
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
    const ready=isFx?i>=l:i>s;
    if(!ready)continue;
    let signal=0;
    if(isFx){
      if(mean(values.slice(i-s,i))>mean(values.slice(i-l,i)))signal=1;
    }else if(values[i-1]<mean(values.slice(i-s-1,i-1))){
      signal=1;
    }
    const changed=signal!==position;
    if(changed){if(signal===1)trades++;position=signal;}
    const baseReturn=isFx
      ? (values[i-1]===0?0:values[i]/values[i-1]-1)
      : -rateDuration*(values[i]-values[i-1]);
    const strategyReturn=(position?baseReturn:0)-(changed?cost:0);
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
        ["Entry","Previous observed yield below the prior lookback mean (falling yields support the long price proxy)"],
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
  const capitalValid=Number.isFinite(value)&&value>0&&Number.isFinite(shock)&&shock>-1&&shock<=5;
  const capitalScenario=capitalValid?applyShock(value,shock):null;
  const stressed=capitalScenario?.ending_value??0;
  const scenarios=[-30,-20,-15,-10,-5,0,5,10,15,20].map(x=>({shock:x,value:value*(1+x/100),pnl:value*x/100}));
  const startingFixedIncome=bond+tbill;
  const fixedIncomeRows=valid?cbkRateScenarios().map(item=>{
    const bondPnl=bondPriceShock(bond,mod,conv,item.rate_change).change;
    const tbillPnl=treasuryBillReinvestmentShock(tbill,effectiveRate,item.rate_change,tenor).income_change;
    return {name:item.name,change:item.rate_change,bondPnl,tbillPnl,totalPnl:bondPnl+tbillPnl,ending:startingFixedIncome+bondPnl+tbillPnl};
  }):[];
  const curveRates=[91,182,364].map(days=>({days,row:latestAuction.find(x=>x.tenor_days===days)})).filter((x): x is {days:number;row:BillRow}=>x.row!==undefined);
  const observedCurve=Object.fromEntries(curveRates.map(({days,row})=>[days,row.rate])) as Record<number,number>;
  const steepened=curveScenario(observedCurve,-.005,.005);
  const flattened=curveScenario(observedCurve,.005,-.005);
  const curveRows=curveRates.map(({days,row})=>({
    days,current:row.rate,steep:steepened[String(days)]?.stressed_rate??row.rate,flat:flattened[String(days)]?.stressed_rate??row.rate
  }));
  return <div className="workspace-stack">
    <Panel title="Capital market shock" note="Apply a direct percentage shock to a user-entered portfolio reference value">
      <div className="metric-grid"><Field label="Reference portfolio value (KES)" value={capital} onChange={setCapital} min="1"/><Field label="Market shock (%)" value={fxShock} onChange={setFxShock} min="-99" max="500"/></div>
      {capitalValid?<><div className="metric-grid"><Metric label="Starting value" value={money(value)}/><Metric label="Profit / loss" value={money(stressed-value)}/><Metric label="Stressed value" value={money(stressed)}/><Metric label="Applied shock" value={pct(shock)}/></div><Table headers={["Scenario","Profit / loss","Stressed value"]} rows={scenarios.map(row=>[row.shock+"%",money(row.pnl),money(row.value)])}/></>:<NoData message="Use a positive reference value and a market shock above −100% and no greater than +500%."/>}
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

    <Panel title="Combined CBK rate-shock impact" note="Bond price effect and Treasury bill reinvestment-income change by scenario">
      {valid?<ChartFrame height={300}><ResponsiveContainer><BarChart data={fixedIncomeRows.map(row=>({scenario:row.name.replace("CBK ",""),bond:row.bondPnl,tbill:row.tbillPnl}))}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7edf2"/>
        <XAxis dataKey="scenario" tick={{fontSize:10,fill:"#8291a0"}}/>
        <YAxis tick={{fontSize:10,fill:"#8291a0"}} width={75}/>
        <ReferenceLine y={0} stroke="#9aa6b2"/>
        <ChartTooltip/>
        <Bar dataKey="bond" name="Bond market-value change (KES)" fill="#356bb3" radius={[3,3,0,0]}/>
        <Bar dataKey="tbill" name="T-bill income change (KES)" fill="#d5a43b" radius={[3,3,0,0]}/>
      </BarChart></ResponsiveContainer></ChartFrame>:<NoData message="Valid bond and Treasury bill assumptions are required to plot fixed-income stress scenarios."/>}
    </Panel>
    <Panel title="Portfolio-value shock curve" note="Deterministic impact across a range of direct market-value shocks">
      <ChartFrame height={260}><ResponsiveContainer><LineChart data={scenarios}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7edf2"/>
        <XAxis dataKey="shock" tick={{fontSize:10,fill:"#8291a0"}} unit="%"/>
        <YAxis tick={{fontSize:10,fill:"#8291a0"}} width={75}/>
        <ReferenceLine x={0} stroke="#9aa6b2"/>
        <ChartTooltip/>
        <Line dataKey="value" name="Stressed portfolio value (KES)" stroke="#c45151" strokeWidth={2.4} dot={{r:3}}/>
      </LineChart></ResponsiveContainer></ChartFrame>
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
