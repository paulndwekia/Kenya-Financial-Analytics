"use client";

import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { ChevronRight, Menu, Moon, RefreshCw, Sun, X } from "lucide-react";
import { MODULES, ModuleWorkspace, type MarketPayload } from "./components/workspaces";

const GROUPS=["Overview","Markets","Fixed income","Quantitative tools","Risk","Portfolio","Research"];

export default function Home(){
  const [active,setActive]=useState("Dashboard");
  const [data,setData]=useState<MarketPayload|null>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  const [dark,setDark]=useState(false);
  const [menu,setMenu]=useState(false);
  const [cookie,setCookie]=useState(false);

  const refreshData=useCallback(async()=>{
    setLoading(true);
    try{
      const response=await fetch("/api/market",{cache:"no-store"});
      const payload=await response.json() as MarketPayload & {error?:string};
      if(!response.ok||!payload.health?.database_connected){
        throw new Error(payload.error||"Market database is not reachable.");
      }
      setData(payload);
      setError("");
    }catch{
      setError("The market data service could not reach its database. Stored market values are not being presented as live.");
    }finally{
      setLoading(false);
    }
  },[]);

  useEffect(()=>{
    setCookie(!localStorage.getItem("kfa-cookie-choice"));
    setDark(localStorage.getItem("kfa-theme")==="dark");
    void refreshData();
    const interval=window.setInterval(()=>void refreshData(),300000);
    return()=>window.clearInterval(interval);
  },[refreshData]);

  const choose=(name:string)=>{
    setActive(name);
    setMenu(false);
    window.scrollTo({top:0,behavior:"smooth"});
  };
  const consent=()=>{
    localStorage.setItem("kfa-cookie-choice","essential-only");
    setCookie(false);
  };
  
  const status=loading&&!data?"CONNECTING":data?.health?.database_connected?"NEON DATABASE":"DATABASE OFFLINE";

  return <div className={dark?"app-shell dark":"app-shell"}>
    <aside className={menu?"sidebar open":"sidebar"}>
      <div className="brand">
        <div className="brand-mark">K</div>
        <div><strong>KENYA FINANCIAL</strong><small>ANALYTICS · RESEARCH TERMINAL</small></div>
        <button className="mobile-menu close-menu" onClick={()=>setMenu(false)} aria-label="Close navigation"><X size={17}/></button>
      </div>
      {GROUPS.map(group=><section className="nav-group" key={group}>
        <div className="nav-label">{group.toUpperCase()}</div>
        <div className="nav-list">
          {MODULES.filter(item=>item.group===group).map(item=>{
            const Icon=item.icon;
            return <button key={item.name} onClick={()=>choose(item.name)} className={active===item.name?"nav-item active":"nav-item"}>
              <Icon size={15} strokeWidth={1.8}/><span>{item.name}</span>
            </button>;
          })}
        </div>
      </section>)}
      <div className="side-foot">
        <div className="source-line"><span className="status-dot"/>{data?.health?.database_connected?"Database connected":"Database status unverified"}</div>
        <div>Market observations attributed to the Central Bank of Kenya.</div>
        <div>© {new Date().getFullYear()} Kenya Financial Analytics</div>
      </div>
    </aside>

    <main className="main">
      <header className="topbar">
        <div className="topbar-left">
          <button className="mobile-menu" onClick={()=>setMenu(true)} aria-label="Open navigation"><Menu size={18}/></button>
          <span className="crumb">Research terminal <ChevronRight size={12} style={{verticalAlign:"middle"}}/> {active}</span>
        </div>
        <div className="top-actions">
          <span className={data?.health?.database_connected?"status-pill":"status-pill status-warning"}>
            <i className="status-dot"/>{status}
          </span>
          <button className="theme-button" onClick={()=>setDark(value=>{const next=!value;localStorage.setItem("kfa-theme",next?"dark":"light");return next;})} aria-label="Toggle colour theme" title="Toggle colour theme">
            {dark?<Sun size={16}/>:<Moon size={16}/>}
          </button>
          <button className="theme-button" onClick={()=>void refreshData()} disabled={loading} aria-label="Refresh data" title="Refresh market data">
            <RefreshCw size={15}/>
          </button>
        </div>
      </header>

      <div className="content">
        <div className="welcome-row">
          <div>
            <div className="eyebrow">KENYAN MARKETS · QUANTITATIVE RESEARCH</div>
            <h1 className="page-title">{active==="Dashboard"?"Market overview":active}</h1>
            <p className="sub-title">{MODULES.find(item=>item.name===active)?.desc}</p>
          </div>
          <div className="date-note"><span>Latest stored CBK observations</span><strong>FX · {data?.health?.latest_fx_observation||"—"}</strong><strong>Treasury bills · {data?.health?.latest_bill_observation||"—"}</strong></div>
        </div>

        {error&&<div className="service-warning"><strong>Data connection needs attention.</strong><span>{error}</span><button className="text-action" onClick={()=>void refreshData()}>Try again</button></div>}

        <AnimatePresence mode="wait">
          <motion.div key={active} initial={{opacity:0,y:5}} animate={{opacity:1,y:0}} exit={{opacity:0,y:-4}} transition={{duration:.2}}>
            <ModuleWorkspace name={active} data={data} loading={loading} error={error}/>
          </motion.div>
        </AnimatePresence>

        <footer className="footer">
          <span>© {new Date().getFullYear()} Kenya Financial Analytics · Independent research workspace</span>
          <span><a href="/privacy">Privacy</a><a href="/terms">Terms</a><a href="/cookies">Cookies</a><a href="https://www.centralbank.go.ke/" target="_blank" rel="noreferrer">CBK source</a></span>
        </footer>
      </div>
    </main>

    {menu&&<button className="mobile-overlay" onClick={()=>setMenu(false)} aria-label="Close navigation overlay"/>}
    {cookie&&<div className="cookie-banner">
      <div><strong style={{fontSize:12}}>Cookie and browser storage notice</strong><p>Essential browser storage remembers your display preference and cookie choice. Optional analytics and advertising trackers are not enabled. Read our <a href="/cookies">cookie notice</a>.</p></div>
      <div className="cookie-actions"><button onClick={consent}>Got it</button></div>
    </div>}
  </div>;
}
