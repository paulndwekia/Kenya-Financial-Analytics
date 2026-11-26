"use client";
import { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Activity, ArrowDownRight, ArrowUpRight, BarChart3, BookOpen, BriefcaseBusiness, ChartNoAxesCombined, ChevronRight, CircleDollarSign, FileText, Gauge, Globe2, Layers3, Menu, Moon, Search, ShieldCheck, Sun, TrendingUp, Wallet, X, Zap, RefreshCw } from "lucide-react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type MarketPoint={date:string;instrument:string;value:number;source:string};
type Payload={ok:boolean;fx:MarketPoint[];bills:{date:string;tenor_days:number;rate:number;source:string}[];source:string;retrieved_at:string|null;health:{fx_rows:number;bills_rows:number;database:string}};
const modules=[
{name:"Dashboard",group:"Overview",desc:"A concise view of Kenyan market conditions and platform activity.",icon:Gauge,color:"#087f8c"},
{name:"Kenyan Market",group:"Markets",desc:"Explore USD, GBP and EUR against the Kenyan shilling.",icon:Globe2,color:"#087f8c"},
{name:"Market Intelligence",group:"Markets",desc:"Market direction, volatility and observation-based signals.",icon:ChartNoAxesCombined,color:"#356bb3"},
{name:"Yield Curve",group:"Fixed income",desc:"Compare the latest available Treasury bill yields by tenor.",icon:TrendingUp,color:"#356bb3"},
{name:"Treasury Bills",group:"Fixed income",desc:"Review auction history and 91, 182 and 364-day instruments.",icon:CircleDollarSign,color:"#d5a43b"},
{name:"Bond Pricing",group:"Fixed income",desc:"Bond valuation, yield to maturity, duration and convexity.",icon:Layers3,color:"#356bb3"},
{name:"Options & Greeks",group:"Quantitative tools",desc:"Black–Scholes valuation and option sensitivity measures.",icon:Zap,color:"#8064b2"},
{name:"Risk Analysis",group:"Risk",desc:"Volatility, value at risk and expected shortfall.",icon:Activity,color:"#c18a35"},
{name:"Risk Intelligence",group:"Risk",desc:"Interpret risk exposures and historical market behaviour.",icon:ShieldCheck,color:"#c18a35"},
{name:"Historical Market Explorer",group:"Research",desc:"Inspect the historical observations available in the data store.",icon:Search,color:"#64748b"},
{name:"Portfolio Intelligence",group:"Portfolio",desc:"Portfolio-level return, risk and diversification analysis.",icon:BriefcaseBusiness,color:"#16835d"},
{name:"Portfolio",group:"Portfolio",desc:"Portfolio construction and allocation workspace.",icon:Wallet,color:"#16835d"},
{name:"Research Intelligence",group:"Research",desc:"Research context, source notes and market observations.",icon:BookOpen,color:"#64748b"},
{name:"Financial Reports",group:"Research",desc:"Prepare clear reports from the available market dataset.",icon:FileText,color:"#64748b"},
{name:"Backtesting",group:"Quantitative tools",desc:"Test historical strategies against available observations.",icon:BarChart3,color:"#8064b2"},
{name:"Stress Testing",group:"Risk",desc:"Explore portfolio and rate-shock scenarios.",icon:Activity,color:"#c45151"}
];
const money=(n:number)=>new Intl.NumberFormat("en-KE",{minimumFractionDigits:2,maximumFractionDigits:4}).format(n);
export default function Home(){
 const [active,setActive]=useState("Dashboard"),[data,setData]=useState<Payload|null>(null),[loading,setLoading]=useState(true),[error,setError]=useState(""),[dark,setDark]=useState(false),[menu,setMenu]=useState(false),[query,setQuery]=useState(""),[cookie,setCookie]=useState(false);
 const refreshData=()=>{setLoading(true);fetch("/api/market",{cache:"no-store"}).then(async r=>{if(!r.ok)throw new Error("Market service returned HTTP "+r.status);const d=await r.json() as Payload;setData(d);setError(d.ok?"":"The data service is reachable, but the connected snapshot has no market observations.");}).catch(()=>setError("Market data service could not be reached. Please try again.")).finally(()=>setLoading(false));};
 useEffect(()=>{setCookie(!localStorage.getItem("kfa-cookie-choice"));setDark(localStorage.getItem("kfa-theme")==="dark");refreshData();const timer=window.setInterval(refreshData,300000);return()=>window.clearInterval(timer);},[]);
 const fx=useMemo(()=>{const grouped=new Map<string,MarketPoint[]>();(data?.fx||[]).forEach(x=>grouped.set(x.instrument,[...(grouped.get(x.instrument)||[]),x]));return grouped;},[data]);
 const latest=(key:string)=>{const rows=fx.get(key)||[];return rows[rows.length-1];};
 const chart=(fx.get("USD/KES")||[]).slice(-45).map(x=>({date:x.date.slice(5),rate:x.value}));
 const visible=modules.filter(m=>m.name.toLowerCase().includes(query.toLowerCase()));
 const choose=(name:string)=>{setActive(name);setMenu(false);window.scrollTo({top:0,behavior:"smooth"});};
 const consent=(v:string)=>{localStorage.setItem("kfa-cookie-choice",v);setCookie(false);};
 const activeModule=modules.find(m=>m.name===active)!;
 return <div className={dark?"app-shell dark":"app-shell"}>
  <aside className={menu?"sidebar open":"sidebar"}>
   <div className="brand"><div className="brand-mark">K</div><div><strong>KENYA FINANCIAL</strong><small>ANALYTICS · RESEARCH TERMINAL</small></div><button className="mobile-menu" onClick={()=>setMenu(false)} aria-label="Close menu"><X size={17}/></button></div>
   <div className="nav-label">WORKSPACE</div><div className="nav-list">{modules.filter(m=>m.group==="Overview").map(m=><NavItem key={m.name} item={m} active={active===m.name} onClick={()=>choose(m.name)}/>)}</div>
   {["Markets","Fixed income","Quantitative tools","Risk","Portfolio","Research"].map(group=><div key={group}><div className="nav-label">{group.toUpperCase()}</div><div className="nav-list">{modules.filter(m=>m.group===group).map(m=><NavItem key={m.name} item={m} active={active===m.name} onClick={()=>choose(m.name)}/>)}</div></div>)}
   <div className="side-foot">Independent Kenyan market analytics<br/>Data provenance: Central Bank of Kenya<br/>© {new Date().getFullYear()} Kenya Financial Analytics</div>
  </aside>
  <main className="main"><header className="topbar"><div style={{display:"flex",alignItems:"center",gap:12}}><button className="mobile-menu" onClick={()=>setMenu(true)} aria-label="Open menu"><Menu size={18}/></button><span className="crumb">Research terminal <ChevronRight size={12} style={{verticalAlign:"middle"}}/> {active}</span></div><div className="top-actions"><span className="status-pill" style={data?.ok&&!error?{}:{background:"#fff8e8",borderColor:"#f1dfb8",color:"#9a6a12"}}><i className="status-dot" style={{background:data?.ok&&!error?"#1b9a6d":"#d39b32",boxShadow:"none"}}/>{loading?"UPDATING":data?.ok&&!error?"CBK DATA AVAILABLE":"DATA NOT VERIFIED"}</span><button className="theme-button" onClick={()=>setDark(v=>{const next=!v;localStorage.setItem("kfa-theme",next?"dark":"light");return next;})} aria-label="Toggle theme">{dark?<Sun size={16}/>:<Moon size={16}/>}</button><button className="theme-button" onClick={refreshData} aria-label="Refresh market data" disabled={loading}><RefreshCw size={15}/></button></div></header>
   <div className="content">
    <AnimatePresence mode="wait"><motion.div key={active} initial={{opacity:0,y:8}} animate={{opacity:1,y:0}} exit={{opacity:0,y:-5}} transition={{duration:.22}}>
     <div className="welcome-row"><div><div className="eyebrow">Kenyan markets · Quantitative research</div><h1 className="page-title">{active==="Dashboard"?"Market overview":active}</h1><p className="sub-title">{active==="Dashboard"?"Market data, fixed income and portfolio risk in one research workspace.":activeModule.desc}</p></div><div className="date-note">Last checked · {data?.retrieved_at?new Date(data.retrieved_at).toLocaleString("en-KE"):"Awaiting data"}</div></div>
     {active==="Dashboard"? <><div className="metric-grid">
      <Metric label="USD / KES" value={latest("USD/KES")?money(latest("USD/KES")!.value):"—"} foot={latest("USD/KES")?.date||"No observation"} accent="#087f8c"/>
      <Metric label="GBP / KES" value={latest("GBP/KES")?money(latest("GBP/KES")!.value):"—"} foot={latest("GBP/KES")?.date||"No observation"} accent="#356bb3"/>
      <Metric label="EUR / KES" value={latest("EUR/KES")?money(latest("EUR/KES")!.value):"—"} foot={latest("EUR/KES")?.date||"No observation"} accent="#d5a43b"/>
      <Metric label="CBK observations" value={(data?.health.fx_rows||0).toLocaleString("en-KE")} foot="Stored FX records" accent="#16835d"/>
     </div>
     <div className="dashboard-grid"><section className="panel"><div className="panel-head"><div><div className="panel-title">USD / KES · Historical reference</div><div className="panel-note">Latest 45 available observations · CBK</div></div><span className="eyebrow">FX MARKET</span></div><div className="chart-wrap">{chart.length?<ResponsiveContainer width="100%" height="100%"><AreaChart data={chart}><defs><linearGradient id="rateFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#087f8c" stopOpacity={.2}/><stop offset="95%" stopColor="#087f8c" stopOpacity={0}/></linearGradient></defs><CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e7edf2"/><XAxis dataKey="date" tick={{fontSize:10,fill:"#8291a0"}} axisLine={false} tickLine={false}/><YAxis domain={["auto","auto"]} tick={{fontSize:10,fill:"#8291a0"}} axisLine={false} tickLine={false} width={48}/><Tooltip contentStyle={{borderRadius:9,border:"1px solid #e4eaf0",fontSize:11}}/><Area type="monotone" dataKey="rate" stroke="#087f8c" strokeWidth={2.2} fill="url(#rateFill)" activeDot={{r:4}}/></AreaChart></ResponsiveContainer>:<div className="empty-state">{loading?"Connecting to the market data store…":"No FX history is currently available."}</div>}</div></section>
     <section className="panel"><div className="panel-head"><div className="panel-title">Market snapshot</div><span className="panel-note">KES per unit</span></div><div className="market-list">{["USD/KES","GBP/KES","EUR/KES"].map(k=>{const p=latest(k);const rows=fx.get(k)||[];const change=rows.length>1?(p!.value/rows[rows.length-2].value-1)*100:null;return <div className="market-row" key={k}><div className="instrument">{k}<small>{p?.date||"No recent record"}</small></div><div className="rate">{p?money(p.value):"—"}</div><span className={change!==null&&change<0?"change down":"change"}>{change===null?"—":<>{change>=0?<ArrowUpRight size={11}/>:<ArrowDownRight size={11}/>} {Math.abs(change).toFixed(3)}%</>}</span></div>})}</div><div style={{marginTop:17,paddingTop:14,borderTop:"1px solid var(--line)"}}><div className="panel-note">TREASURY BILL RECORDS</div><div className="metric-value" style={{fontSize:22}}>{(data?.health.bills_rows||0).toLocaleString("en-KE")}</div><div className="metric-foot">Official observations in the database</div></div></section></div>
     </>:<ModuleView name={active} data={data} fx={fx} loading={loading} error={error}/>}
     <div className="section-head"><div><h2>{active==="Dashboard"?"Research modules":"Explore another module"}</h2><p>Sixteen connected workspaces across Kenyan markets and quantitative finance.</p></div><input className="search" placeholder="Find a module…" value={query} onChange={e=>setQuery(e.target.value)}/></div>
     <div className="module-grid">{visible.map(m=><button key={m.name} className="module-card" onClick={()=>choose(m.name)} style={{"--accent":m.color} as React.CSSProperties}><span className="module-icon"><m.icon size={17}/></span><div className="module-name">{m.name}</div><div className="module-desc">{m.desc}</div></button>)}</div>
     <footer className="footer"><span>© {new Date().getFullYear()} Kenya Financial Analytics · Independent research workspace</span><span><a href="/privacy">Privacy</a><a href="/terms">Terms</a><a href="/cookies">Cookies</a><a href="https://www.centralbank.go.ke/" target="_blank" rel="noreferrer">CBK source</a></span></footer>
    </motion.div></AnimatePresence>
   </div></main>
  {cookie&&<div className="cookie-banner"><div><strong style={{fontSize:12}}>A note about cookies</strong><p>We use essential browser storage to remember your display preferences and cookie choice. No analytics or advertising cookies are enabled. Read our <a href="/cookies" style={{color:"#9edadd"}}>cookie notice</a>.</p></div><div className="cookie-actions"><button className="secondary" onClick={()=>consent("essential-only")}>Essential only</button><button onClick={()=>consent("essential-only")}>Got it</button></div></div>}
 </div>;
}
function NavItem({item,active,onClick}:{item:any;active:boolean;onClick:()=>void}){const Icon=item.icon;return <button onClick={onClick} className={active?"nav-item active":"nav-item"}><span className="nav-dot" style={{"--accent":item.color} as React.CSSProperties}/>{item.name}</button>}
function Metric({label,value,foot,accent}:{label:string;value:string;foot:string;accent:string}){return <motion.div className="metric-card" initial={{opacity:0,y:8}} animate={{opacity:1,y:0}} transition={{duration:.3}}><div className="metric-label">{label}<span style={{height:7,width:7,borderRadius:9,background:accent}}/></div><div className="metric-value">{value}</div><div className="metric-foot">{foot}</div></motion.div>}
function Field({label,value,onChange,type="number",step="any"}:{label:string;value:string;onChange:(v:string)=>void;type?:string;step?:string}){
 return <label style={{display:"grid",gap:6,fontSize:11,color:"var(--muted)"}}>{label}<input className="search" type={type} step={step} value={value} onChange={e=>onChange(e.target.value)}/></label>;
}
function Result({label,value,note}:{label:string;value:string;note?:string}){
 return <div className="metric-card"><div className="metric-label">{label}</div><div className="metric-value" style={{fontSize:20}}>{value}</div>{note&&<div className="metric-foot">{note}</div>}</div>;
}
function ModuleView({name,data,fx,loading,error}:{name:string;data:Payload|null;fx:Map<string,MarketPoint[]>;loading:boolean;error:string}) {
 const all=(data?.fx||[]).filter(x=>x.instrument);
 const bills=data?.bills||[];
 const [face,setFace]=useState("100000"),[coupon,setCoupon]=useState("12"),[ytm,setYtm]=useState("13"),[years,setYears]=useState("5"),[freq,setFreq]=useState("2");
 const [days,setDays]=useState("182"),[billYield,setBillYield]=useState("9"),[billFace,setBillFace]=useState("100000");
 const [spot,setSpot]=useState("100"),[strike,setStrike]=useState("100"),[term,setTerm]=useState("1"),[rate,setRate]=useState("13"),[sigma,setSigma]=useState("20"),[option,setOption]=useState("Call");
 const [instrument,setInstrument]=useState("USD/KES"),[capital,setCapital]=useState("1000000"),[shock,setShock]=useState("-10");
 const [portfolio,setPortfolio]=useState([{name:"91-Day Treasury Bill",value:"300000",expected:"8.5",vol:"2"},{name:"182-Day Treasury Bill",value:"300000",expected:"8.8",vol:"2.5"},{name:"Government Bond",value:"400000",expected:"10",vol:"8"}]);
 const [report,setReport]=useState(false);
 const fmt=(v:number)=>"KES "+new Intl.NumberFormat("en-KE",{minimumFractionDigits:2,maximumFractionDigits:2}).format(v);
 const n=(v:string)=>Number.isFinite(Number(v))?Number(v):0;
 const pcts=(v:string)=>n(v)/100;
 const fxRows=fx.get(instrument)||[];
 const prices=fxRows.map(x=>x.value).filter(v=>v>0&&Number.isFinite(v));
 const returns=prices.slice(1).map((v,i)=>v/prices[i]-1).filter(Number.isFinite);
 const mean=(xs:number[])=>xs.length?xs.reduce((a,b)=>a+b,0)/xs.length:0;
 const stdev=(xs:number[])=>xs.length>1?Math.sqrt(xs.reduce((s,x)=>s+(x-mean(xs))**2,0)/(xs.length-1)):0;
 const percentile=(xs:number[],q:number)=>{if(!xs.length)return 0;const a=[...xs].sort((x,y)=>x-y);return a[Math.max(0,Math.min(a.length-1,Math.floor(q*(a.length-1))))]};
 const f=n(face),c=pcts(coupon),y=pcts(ytm),m=Math.max(1,n(freq)),periods=Math.max(1,Math.round(n(years)*m));
 const cp=f*c/m,pr=y/m;
 const bondPrice=periods>0?Array.from({length:periods},(_,i)=>(cp+(i===periods-1?f:0))/Math.pow(1+pr,i+1)).reduce((a,b)=>a+b,0):0;
 const macDuration=bondPrice>0?Array.from({length:periods},(_,i)=>((i+1)/m)*(cp+(i===periods-1?f:0))/Math.pow(1+pr,i+1)).reduce((a,b)=>a+b,0)/bondPrice:0;
 const modDuration=macDuration/(1+pr);
 const convexity=bondPrice>0?Array.from({length:periods},(_,i)=>((i+1)*(i+2)*(cp+(i===periods-1?f:0))/(m*m*Math.pow(1+pr,i+3)))).reduce((a,b)=>a+b,0)/bondPrice:0;
 const billPrice=n(billFace)/(1+pcts(billYield)*n(days)/365);
 const S=n(spot),K=n(strike),T=n(term),rr=pcts(rate),vol=pcts(sigma);
 const cdf=(x:number)=>{const sign=x<0?-1:1,z=Math.abs(x)/Math.sqrt(2),t=1/(1+0.3275911*z),a=1-(((((1.061405429*t-1.453152027)*t)+1.421413741)*t-0.284496736)*t+0.254829592)*t*Math.exp(-z*z);return .5*(1+sign*a)};
 const d1=S>0&&K>0&&T>0&&vol>0?(Math.log(S/K)+(rr+vol*vol/2)*T)/(vol*Math.sqrt(T)):0;
 const d2=d1-vol*Math.sqrt(Math.max(0,T));
 const optionPrice=S>0&&K>0&&T>0&&vol>0?(option==="Call"?S*cdf(d1)-K*Math.exp(-rr*T)*cdf(d2):K*Math.exp(-rr*T)*cdf(-d2)-S*cdf(-d1)):0;
 const annualVol=stdev(returns)*Math.sqrt(252);
 const var95=Math.max(0,-percentile(returns,.05)*n(capital));
 const esTail=returns.filter(x=>x<=percentile(returns,.05));
 const es95=esTail.length?Math.max(0,-mean(esTail)*n(capital)):0;
 const peak=prices.reduce((a,b)=>Math.max(a,b),0);
 const drawdown=prices.length?Math.min(...prices.map((v,i)=>v/Math.max(...prices.slice(0,i+1))-1)):0;
 const portfolioItems=portfolio.map(x=>({...x,v:n(x.value),e:pcts(x.expected),s:pcts(x.vol)}));
 const total=portfolioItems.reduce((a,x)=>a+x.v,0);
 const weights=portfolioItems.map(x=>total?x.v/total:0);
 const expected=portfolioItems.reduce((a,x,i)=>a+weights[i]*x.e,0);
 const pVol=Math.sqrt(portfolioItems.reduce((a,x,i)=>a+weights[i]**2*x.s**2,0));
 const pVaR=1.64485*pVol*total/Math.sqrt(252);
 const setPort=(i:number,key:"name"|"value"|"expected"|"vol",value:string)=>setPortfolio(prev=>prev.map((item,j)=>i===j?{...item,[key]:value}:item));
 const downloadReport=()=>{
  const body=["KENYA FINANCIAL ANALYTICS","Research summary","Generated: "+new Date().toISOString(),"Data source: Central Bank of Kenya","FX observations: "+all.length,"Treasury bill observations: "+bills.length,"","This document is an analytical summary, not investment advice."].join("\n");
  const blob=new Blob([body],{type:"text/plain;charset=utf-8"}),url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download="kenya-financial-analytics-summary.txt";a.click();URL.revokeObjectURL(url);
 };
 if(name==="Kenyan Market"||name==="Historical Market Explorer"||name==="Market Intelligence") return <section className="panel">
  <div className="panel-head"><div><div className="panel-title">{name==="Market Intelligence"?"Market observations and direction":name==="Kenyan Market"?"Kenyan FX market":"Historical market explorer"}</div><div className="panel-note">Published CBK observations available in the connected snapshot</div></div><select className="search" value={instrument} onChange={e=>setInstrument(e.target.value)} style={{minWidth:130}}><option>USD/KES</option><option>GBP/KES</option><option>EUR/KES</option></select></div>
  <div className="metric-grid"><Result label="Latest rate" value={prices.length?money(prices[prices.length-1]):"—"} note={fxRows.at(-1)?.date||"No date available"}/><Result label="Observations" value={String(fxRows.length)} note="Records for selected pair"/><Result label="Annualised volatility" value={returns.length?(annualVol*100).toFixed(2)+"%":"—"} note="Historical sample estimate"/><Result label="Maximum drawdown" value={prices.length?(drawdown*100).toFixed(2)+"%":"—"} note="From observed price series"/></div>
  <div style={{overflowX:"auto"}}><table className="data-table"><thead><tr><th>Date</th><th>Instrument</th><th>Rate</th><th>Publisher</th></tr></thead><tbody>{fxRows.slice(-150).reverse().map((r,i)=><tr key={i}><td>{r.date}</td><td>{r.instrument}</td><td>{money(r.value)}</td><td>{r.source}</td></tr>)}</tbody></table></div>
  {!fxRows.length&&<div className="empty-state">{loading?"Loading available observations…":error||"The connected data snapshot has no records for this currency pair."}</div>}
 </section>;
 if(name==="Yield Curve"||name==="Treasury Bills") {
  const latestDate=bills.reduce((a,b)=>!a||b.date>a?b.date:a,"");
  const latest=bills.filter(b=>b.date===latestDate).sort((a,b)=>a.tenor_days-b.tenor_days);
  return <section className="panel"><div className="panel-head"><div><div className="panel-title">{name==="Yield Curve"?"Latest available Treasury yield curve":"Treasury bill auction history"}</div><div className="panel-note">Based on recorded CBK auction results; no rates are interpolated in this view.</div></div><span className="eyebrow">{latestDate||"NO RECORDS"}</span></div>
  {name==="Yield Curve"&&<div className="metric-grid">{[91,182,364].map(t=>{const b=latest.find(x=>x.tenor_days===t);return <Result key={t} label={t+"-day yield"} value={b?(b.rate*100).toFixed(4)+"%":"—"} note={b?.date||"No observation for latest auction"}/>})}</div>}
  <div style={{overflowX:"auto"}}><table className="data-table"><thead><tr><th>Auction date</th><th>Tenor</th><th>Accepted yield</th><th>Source</th></tr></thead><tbody>{bills.slice(-180).reverse().map((b,i)=><tr key={i}><td>{b.date}</td><td>{b.tenor_days}-day</td><td>{(b.rate*100).toFixed(4)}%</td><td>{b.source}</td></tr>)}</tbody></table></div>{!bills.length&&<div className="empty-state">No Treasury bill observations are available in the connected database snapshot.</div>}</section>;
 }
 if(name==="Bond Pricing")return <section className="panel"><div className="panel-head"><div><div className="panel-title">Fixed-rate bond valuation</div><div className="panel-note">Periodic coupon discounting · default semi-annual payment frequency</div></div><span className="eyebrow">KES DENOMINATED</span></div><div className="metric-grid" style={{gridTemplateColumns:"repeat(auto-fit,minmax(150px,1fr))"}}><Field label="Face value (KES)" value={face} onChange={setFace}/><Field label="Annual coupon (%)" value={coupon} onChange={setCoupon}/><Field label="Yield to maturity (%)" value={ytm} onChange={setYtm}/><Field label="Years to maturity" value={years} onChange={setYears}/><Field label="Payments per year" value={freq} onChange={setFreq}/></div><div className="metric-grid"><Result label="Model price" value={fmt(bondPrice)} note={bondPrice>f?"Premium to par":bondPrice<f?"Discount to par":"At par"}/><Result label="Macaulay duration" value={macDuration.toFixed(4)+" yrs"}/><Result label="Modified duration" value={modDuration.toFixed(4)}/><Result label="Convexity" value={convexity.toFixed(4)}/></div><p className="panel-note">This uses standard periodic coupon discounting. Actual Kenyan government security pricing can require day-count, settlement and accrued-interest conventions that are not represented in this simplified calculator.</p></section>;
 if(name==="Options & Greeks")return <section className="panel"><div className="panel-head"><div><div className="panel-title">Black–Scholes option calculator</div><div className="panel-note">European option model; volatility and rates are user inputs.</div></div><select className="search" value={option} onChange={e=>setOption(e.target.value)}><option>Call</option><option>Put</option></select></div><div className="metric-grid" style={{gridTemplateColumns:"repeat(auto-fit,minmax(150px,1fr))"}}><Field label="Underlying price" value={spot} onChange={setSpot}/><Field label="Strike price" value={strike} onChange={setStrike}/><Field label="Time to expiry (years)" value={term} onChange={setTerm}/><Field label="Risk-free rate (%)" value={rate} onChange={setRate}/><Field label="Volatility (%)" value={sigma} onChange={setSigma}/></div><div className="metric-grid"><Result label="Model option value" value={fmt(optionPrice)}/><Result label="Delta" value={(option==="Call"?cdf(d1):cdf(d1)-1).toFixed(4)}/><Result label="Gamma" value={(S>0&&vol>0&&T>0?Math.exp(-d1*d1/2)/Math.sqrt(2*Math.PI)/(S*vol*Math.sqrt(T)):0).toFixed(5)}/><Result label="Vega (per 1% vol)" value={(S>0&&T>0?S*Math.exp(-d1*d1/2)/Math.sqrt(2*Math.PI)*Math.sqrt(T)/100:0).toFixed(4)}/></div><p className="panel-note">Model assumptions exclude dividends, early exercise and transaction costs. Confirm inputs and model suitability before relying on outputs.</p></section>;
 if(name==="Risk Analysis"||name==="Risk Intelligence")return <section className="panel"><div className="panel-head"><div><div className="panel-title">{name==="Risk Analysis"?"Historical FX risk measures":"Market risk observations"}</div><div className="panel-note">Uses the selected CBK FX history as a proxy series, not a diversified asset portfolio.</div></div><select className="search" value={instrument} onChange={e=>setInstrument(e.target.value)}><option>USD/KES</option><option>GBP/KES</option><option>EUR/KES</option></select></div><div className="metric-grid" style={{gridTemplateColumns:"repeat(auto-fit,minmax(150px,1fr))"}}><Field label="Portfolio value (KES)" value={capital} onChange={setCapital}/></div><div className="metric-grid"><Result label="Annualised volatility" value={returns.length?(annualVol*100).toFixed(2)+"%":"—"}/><Result label="Historical VaR · 95%" value={returns.length?fmt(var95):"—"} note="One-observation empirical tail approximation"/><Result label="Expected shortfall · 95%" value={returns.length?fmt(es95):"—"} note="Mean observed loss in the empirical 5% tail"/><Result label="Maximum drawdown" value={prices.length?(drawdown*100).toFixed(2)+"%":"—"}/></div>{returns.length<2&&<div className="empty-state">At least three valid price observations are needed to estimate historical returns and risk.</div>}</section>;
 if(name==="Portfolio"||name==="Portfolio Intelligence"||name==="Stress Testing"||name==="Backtesting"){
  const stressed=total*(1+n(shock)/100);
  return <section className="panel"><div className="panel-head"><div><div className="panel-title">{name==="Stress Testing"?"Portfolio shock scenario":name==="Backtesting"?"Historical observation review": "Portfolio allocation workspace"}</div><div className="panel-note">Illustrative inputs supplied by the user. Nothing is saved or transmitted.</div></div><span className="eyebrow">LOCAL CALCULATOR</span></div>
   <div style={{overflowX:"auto"}}><table className="data-table"><thead><tr><th>Position</th><th>Value (KES)</th><th>Expected return (%)</th><th>Volatility (%)</th></tr></thead><tbody>{portfolio.map((item,i)=><tr key={i}><td><input className="search" value={item.name} onChange={e=>setPort(i,"name",e.target.value)} style={{minWidth:140}}/></td><td><input className="search" value={item.value} onChange={e=>setPort(i,"value",e.target.value)} style={{minWidth:100}}/></td><td><input className="search" value={item.expected} onChange={e=>setPort(i,"expected",e.target.value)} style={{minWidth:90}}/></td><td><input className="search" value={item.vol} onChange={e=>setPort(i,"vol",e.target.value)} style={{minWidth:90}}/></td></tr>)}</tbody></table></div>
   <div style={{display:"flex",gap:8,marginTop:12,flexWrap:"wrap"}}><button className="primary-btn" onClick={()=>setPortfolio(v=>[...v,{name:"New position",value:"0",expected:"0",vol:"0"}])}>Add position</button><button className="theme-button" onClick={()=>setPortfolio(v=>v.length>1?v.slice(0,-1):v)}>Remove last position</button></div>
   {name==="Stress Testing"&&<div style={{maxWidth:260,marginTop:16}}><Field label="Portfolio shock (%)" value={shock} onChange={setShock}/></div>}
   <div className="metric-grid"><Result label="Portfolio value" value={fmt(total)}/><Result label="Weighted expected return" value={(expected*100).toFixed(2)+"%"}/><Result label="Volatility estimate" value={(pVol*100).toFixed(2)+"%"} note="Independent-position approximation"/><Result label={name==="Stress Testing"?"Stressed portfolio value":"Parametric VaR · 95%"} value={name==="Stress Testing"?fmt(stressed):fmt(pVaR)}/></div>
   {name==="Portfolio Intelligence"&&<p className="panel-note">Volatility assumes zero correlation between positions. A covariance matrix is needed for a fuller portfolio risk estimate.</p>}
   {name==="Backtesting"&&<p className="panel-note">This first review view reports input portfolio characteristics. A proper strategy backtest with transaction costs and rebalancing rules remains to be implemented rather than shown as simulated performance.</p>}
  </section>;
 }
 if(name==="Financial Reports"||name==="Research Intelligence")return <section className="panel"><div className="panel-head"><div><div className="panel-title">{name==="Financial Reports"?"Research data summary":"Research provenance"}</div><div className="panel-note">The figures below reflect only the currently connected historical snapshot.</div></div><button className="primary-btn" onClick={downloadReport}>Export data summary</button></div><div className="metric-grid"><Result label="FX records" value={String(all.length)}/><Result label="Treasury bill records" value={String(bills.length)}/><Result label="Data publisher" value="CBK"/><Result label="Snapshot retrieved" value={data?.retrieved_at?new Date(data.retrieved_at).toLocaleDateString("en-KE"):"Not confirmed"}/></div><p className="panel-note">The exported summary records coverage and provenance only; it does not manufacture market observations or imply that unverified data feeds are live.</p></section>;
 const faceValue=n(billFace);
 if(name==="Treasury Bills")return null;
 return <section className="panel"><div className="panel-head"><div className="panel-title">Treasury bill price calculator</div><span className="eyebrow">365-DAY BASIS</span></div><div className="metric-grid" style={{gridTemplateColumns:"repeat(auto-fit,minmax(150px,1fr))"}}><Field label="Face value (KES)" value={billFace} onChange={setBillFace}/><Field label="Annual investment yield (%)" value={billYield} onChange={setBillYield}/><Field label="Tenor (days)" value={days} onChange={setDays}/></div><div className="metric-grid"><Result label="Estimated purchase price" value={fmt(billPrice)}/><Result label="Discount to face" value={fmt(faceValue-billPrice)}/><Result label="Tenor" value={days+" days"}/></div><p className="panel-note">The calculation follows the pricing convention documented in the retained Treasury bill pricing engine. Actual auction terms and tax treatment may differ.</p></section>;
}