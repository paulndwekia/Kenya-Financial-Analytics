# -*- coding: utf-8 -*-
"""
Kenya Financial Analytics - Unified Desktop Dashboard
Uses the existing project engines and databases without requiring the old
Streamlit dashboard or desktop launcher.
"""
from __future__ import annotations
import os, sqlite3, math
from pathlib import Path
from datetime import date, datetime, timedelta
import numpy as np
import pandas as pd
import streamlit as st

try:
    import plotly.express as px
    PLOTLY = True
except Exception:
    PLOTLY = False

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("KFA_DATA_DIR", str(BASE_DIR))).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB = DATA_DIR / "kenya_market.db"

st.set_page_config(page_title="Kenya Financial Analytics", page_icon="🇰🇪", layout="wide", initial_sidebar_state="expanded")

# ---------- database compatibility ----------
def connect():
    return sqlite3.connect(DB, check_same_thread=False)

def tables():
    if not DB.exists(): return []
    with connect() as c:
        return [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]

def cols(table):
    if table not in tables(): return []
    with connect() as c:
        return [r[1] for r in c.execute(f'PRAGMA table_info("{table}")')]

def q(sql, params=()):
    try:
        with connect() as c: return pd.read_sql_query(sql, c, params=params)
    except Exception as e:
        raise RuntimeError(f"Database query failed: {e}") from e

def ensure_db():
    with connect() as c:
        c.execute("CREATE TABLE IF NOT EXISTS market_data (id INTEGER PRIMARY KEY AUTOINCREMENT, trade_date TEXT, instrument TEXT, price REAL, yield REAL, volume REAL, source TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS treasury_bills (id INTEGER PRIMARY KEY AUTOINCREMENT, auction_date TEXT, tenor_days INTEGER, accepted_rate REAL, weighted_average_rate REAL, amount_offered REAL, amount_accepted REAL, source TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS bonds (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, maturity TEXT, coupon REAL, face_value REAL, market_price REAL, yield REAL)")
        c.execute("CREATE TABLE IF NOT EXISTS portfolio (id INTEGER PRIMARY KEY AUTOINCREMENT, asset TEXT, quantity REAL, price REAL, weight REAL)")
        c.execute("CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY AUTOINCREMENT, report_date TEXT, report_type TEXT, content TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS treasury_bill_rates (id INTEGER PRIMARY KEY AUTOINCREMENT, auction_date TEXT NOT NULL, tenor_days INTEGER NOT NULL, rate REAL NOT NULL, issue_number TEXT, source TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(auction_date, tenor_days))")

def market_df():
    if 'market_data' not in tables(): return pd.DataFrame()
    c=cols('market_data')
    d='trade_date' if 'trade_date' in c else ('date' if 'date' in c else None)
    y='yield' if 'yield' in c else ('yield_rate' if 'yield_rate' in c else None)
    if not d: return pd.DataFrame()
    ys=f', "{y}" AS yield' if y else ', 0.0 AS yield'
    return q(f'SELECT id, "{d}" AS trade_date, instrument, price{ys}, volume, source FROM market_data ORDER BY "{d}"')

def tbill_df():
    if 'treasury_bills' not in tables(): return pd.DataFrame()
    c=cols('treasury_bills')
    r='accepted_rate' if 'accepted_rate' in c else ('weighted_average_rate' if 'weighted_average_rate' in c else None)
    d='auction_date' if 'auction_date' in c else None
    if not r or not d: return pd.DataFrame()
    return q(f'SELECT *, "{r}" AS rate FROM treasury_bills ORDER BY tenor_days, "{d}"')

def cbk_history():
    if 'treasury_bill_rates' not in tables(): return pd.DataFrame()
    return q('SELECT auction_date, tenor_days, rate, issue_number, source FROM treasury_bill_rates ORDER BY auction_date')

def norm_rate(x):
    try:
        x=float(x); return x/100 if abs(x)>1 else x
    except: return np.nan

# ---------- core quantitative tools ----------
def norm_cdf(x): return 0.5*(1+math.erf(x/math.sqrt(2)))
def norm_pdf(x): return math.exp(-0.5*x*x)/math.sqrt(2*math.pi)
def bs(S,K,T,r,sigma,kind):
    if S<=0 or K<=0 or T<=0 or sigma<=0: return np.nan
    d1=(math.log(S/K)+(r+0.5*sigma*sigma)*T)/(sigma*math.sqrt(T)); d2=d1-sigma*math.sqrt(T)
    if kind=='Call': return S*norm_cdf(d1)-K*math.exp(-r*T)*norm_cdf(d2)
    return K*math.exp(-r*T)*norm_cdf(-d2)-S*norm_cdf(-d1)
def greeks(S,K,T,r,sigma,kind):
    d1=(math.log(S/K)+(r+0.5*sigma*sigma)*T)/(sigma*math.sqrt(T)); d2=d1-sigma*math.sqrt(T); nd=norm_pdf(d1)
    delta=norm_cdf(d1) if kind=='Call' else norm_cdf(d1)-1
    gamma=nd/(S*sigma*math.sqrt(T)); vega=S*nd*math.sqrt(T)/100
    theta=(-S*nd*sigma/(2*math.sqrt(T))-r*K*math.exp(-r*T)*(norm_cdf(d2) if kind=='Call' else norm_cdf(-d2)))/365
    rho=(K*T*math.exp(-r*T)*norm_cdf(d2 if kind=='Call' else -d2))/100
    return {'Delta':delta,'Gamma':gamma,'Vega':vega,'Theta':theta,'Rho':rho}
def bond_price(face,coupon,yield_rate,years,freq=2):
    n=max(1,int(round(years*freq))); c=face*coupon/freq; y=yield_rate/freq
    return sum(c/(1+y)**t for t in range(1,n+1))+face/(1+y)**n
def tbill_price(face,rate,days): return face/(1+rate*days/365)
def var(returns,conf=.95): return -np.percentile(returns,(1-conf)*100) if len(returns)>1 else np.nan
def max_dd(v):
    v=np.asarray(v,float); m=np.maximum.accumulate(v); return abs(np.min((v-m)/m)) if len(v) else np.nan

def run_external(module, func):
    try:
        mod=__import__(module, fromlist=[func]); getattr(mod,func)()
    except Exception as e:
        st.error(f"{module} could not be loaded: {type(e).__name__}: {e}")
        st.info("The rest of the platform remains available. Check the module/database status below.")

# ---------- pages ----------
def home():
    st.title('🇰🇪 Kenya Financial Analytics')
    st.caption('Unified Quantitative Finance Research & Analytics Platform')
    m=market_df(); h=cbk_history(); t=tbill_df()
    a,b,c,d=st.columns(4); a.metric('Market Records',len(m)); b.metric('CBK T-Bill History',len(h)); c.metric('T-Bill Records',len(t)); d.metric('Database','ONLINE' if DB.exists() else 'NEW')
    st.divider(); st.subheader('Platform Modules')
    mods=['Kenyan Market','Treasury Bills','Bond Pricing','Options & Greeks','Yield Curve','Portfolio','Risk Analysis','Historical Market Explorer','Market Intelligence','Risk Intelligence','Portfolio Intelligence','Research Intelligence','Backtesting','Stress Testing','Financial Reports','Command Center']
    for i in range(0,len(mods),4):
        cs=st.columns(4)
        for j,name in enumerate(mods[i:i+4]): cs[j].info(name)
    st.success('Unified platform loaded. Use the navigation menu to open every available application.')

def market():
    st.title('🇰🇪 Kenyan Market')
    df=market_df()
    if df.empty: st.warning('No compatible market_data records found.'); return
    df['trade_date']=pd.to_datetime(df['trade_date'],errors='coerce'); inst=sorted(df.instrument.dropna().unique()); sel=st.selectbox('Instrument',inst); x=df[df.instrument==sel].copy(); last=x.iloc[-1]
    a,b,c=st.columns(3); a.metric('Latest Price',f"{float(last.price):,.4f}"); b.metric('Yield',f"{float(last['yield']):.2f}%"); c.metric('Records',len(x))
    if PLOTLY: st.plotly_chart(px.line(x,x='trade_date',y='price',title=f'{sel} Historical Price'),use_container_width=True)
    st.dataframe(x.tail(100),use_container_width=True)

def tbills():
    st.title('💰 Treasury Bills')
    df=tbill_df(); h=cbk_history()
    if not df.empty: st.dataframe(df,use_container_width=True)
    if not h.empty:
        st.subheader('Historical CBK Treasury Bill Rates'); st.dataframe(h.tail(100),use_container_width=True)
    st.subheader('T-Bill Calculator'); a,b,c=st.columns(3); face=a.number_input('Face Value (KES)',1000.,10_000_000.,100_000.); rate=b.number_input('Annual Yield (%)',0.,100.,15.); days=c.number_input('Days',1,1000,91)
    price=tbill_price(face,rate/100,days); st.metric('Purchase Price',f'KES {price:,.2f}'); st.metric('Discount / Return',f'KES {face-price:,.2f}')

def bonds():
    st.title('🏦 Bond Pricing'); a,b,c=st.columns(3); face=a.number_input('Face Value',1000.,100_000_000.,100_000.); coupon=b.number_input('Coupon Rate (%)',0.,100.,12.); years=c.number_input('Years to Maturity',0.25,50.,5.); y=st.number_input('Required Yield (%)',0.,100.,13.)
    st.metric('Estimated Bond Price',f'KES {bond_price(face,coupon/100,y/100,years):,.2f}')
    if 'bonds' in tables(): st.dataframe(q('SELECT * FROM bonds'),use_container_width=True)

def options():
    st.title('📈 Options & Greeks'); a,b,c=st.columns(3); S=a.number_input('Underlying Price',0.01,1e9,100.); K=b.number_input('Strike Price',0.01,1e9,100.); T=c.number_input('Time to Expiry (Years)',0.01,100.,1.); d,e,f=st.columns(3); r=d.number_input('Risk-Free Rate (%)',-20.,100.,10.); sig=e.number_input('Volatility (%)',0.01,500.,20.); kind=f.selectbox('Option Type',['Call','Put']); p=bs(S,K,T,r/100,sig/100,kind); st.metric(f'Black-Scholes {kind}',f'{p:,.4f}'); g=greeks(S,K,T,r/100,sig/100,kind); cs=st.columns(5)
    for col,(k,v) in zip(cs,g.items()): col.metric(k,f'{v:.6f}')

def curve():
    st.title('📊 Kenya Yield Curve'); h=cbk_history();
    if h.empty: st.warning('No historical CBK curve data available.'); return
    latest=h.sort_values('auction_date').groupby('tenor_days',as_index=False).tail(1).copy(); latest['rate']=latest.rate.map(norm_rate)*100; latest=latest.sort_values('tenor_days');
    if PLOTLY: st.plotly_chart(px.line(latest,x='tenor_days',y='rate',markers=True,title='Latest CBK Treasury Bill Curve'),use_container_width=True)
    st.dataframe(latest,use_container_width=True)

def portfolio():
    st.title('💼 Portfolio Analytics'); assets=['91-Day T-Bill','182-Day T-Bill','364-Day T-Bill','Government Bond','Cash']; rows=[]
    for x in assets:
        w=st.slider(f'{x} Weight (%)',0.,100.,0.,1.); rows.append((x,w))
    p=pd.DataFrame(rows,columns=['Asset','Weight']); total=p.Weight.sum();
    if total: p['Normalized Weight']=p.Weight/total; st.dataframe(p,use_container_width=True); st.metric('Total Allocated',f'{total:.2f}%')
    else: st.info('Select portfolio weights above.')

def risk():
    st.title('⚠️ Risk Analysis'); df=market_df();
    if df.empty: st.warning('No market data.'); return
    instruments=sorted(df.instrument.dropna().unique()); sel=st.selectbox('Risk Instrument',instruments); x=df[df.instrument==sel].copy(); x['price']=pd.to_numeric(x.price,errors='coerce'); r=x.price.pct_change().dropna();
    a,b,c=st.columns(3); a.metric('95% Daily VaR',f'{var(r)*100:.2f}%'); b.metric('Max Drawdown',f'{max_dd(x.price.dropna().values)*100:.2f}%'); c.metric('Observations',len(r))

def historical():
    st.title('🗄️ Historical Market Explorer'); df=market_df();
    if df.empty: st.warning('Historical market database is empty.'); return
    df['trade_date']=pd.to_datetime(df.trade_date,errors='coerce'); inst=sorted(df.instrument.dropna().unique()); selected=st.multiselect('Instruments',inst,default=inst[:1]); start=st.date_input('Start Date',date.today()-timedelta(days=365)); end=st.date_input('End Date',date.today()); x=df[df.instrument.isin(selected)] if selected else df; x=x[(x.trade_date.dt.date>=start)&(x.trade_date.dt.date<=end)]; st.dataframe(x,use_container_width=True); st.download_button('Download CSV',x.to_csv(index=False),'kenya_historical_market_data.csv','text/csv')

def backtest():
    st.title('🔬 Backtesting')
    try:
        mod=__import__('backtest_engine',fromlist=['*'])
        if hasattr(mod,'render_backtesting'): mod.render_backtesting()
        elif hasattr(mod,'compare_tenors'):
            tenor=st.selectbox('Tenor',[91,182,364]); st.json(mod.compare_tenors(tenor))
        else: st.info('Backtesting engine is installed but has no Streamlit renderer. Core engine is available.')
    except Exception as e: st.error(f'Backtesting engine error: {e}')
def stress():
    st.title('💥 Stress Testing')
    try:
        mod=__import__('stress_engine',fromlist=['*'])
        if hasattr(mod,'render_stress_testing'): mod.render_stress_testing()
        elif hasattr(mod,'stress_report'):
            value=st.number_input('Portfolio Value (KES)',1000.,1_000_000_000.,1_000_000.); shock=st.slider('Market Shock (%)',-50.,50.,-10.)/100; st.json(mod.apply_shock(value,shock))
        else: st.info('Stress engine is installed but has no Streamlit renderer. Core engine is available.')
    except Exception as e: st.error(f'Stress engine error: {e}')
def reports(): run_external('kenya_financial_reports','render_financial_reports')
def market_intel(): run_external('kenya_market_intelligence','render_market_intelligence')
def risk_intel(): run_external('kenya_risk_intelligence','render_risk_intelligence')
def portfolio_intel(): run_external('kenya_portfolio_intelligence','render_portfolio_intelligence')
def research_intel(): run_external('kenya_research_intelligence','render_research_intelligence')

def command():
    st.title('🧭 Command Center'); st.write(f'Database: `{DB}`'); st.write('Tables:'); st.dataframe(pd.DataFrame({'Table':tables()}),use_container_width=True)
    files=['pricing_engine.py','cbk_pricing.py','risk_engine.py','portfolio_engine.py','backtest_engine.py','stress_engine.py','fixed_income.py','yield_curve.py','historical_data.py','kenya_market_intelligence.py','kenya_risk_intelligence.py','kenya_portfolio_intelligence.py','kenya_research_intelligence.py','kenya_financial_reports.py']
    st.dataframe(pd.DataFrame({'Module':files,'Status':['ONLINE' if (BASE_DIR/x).exists() else 'MISSING' for x in files]}),use_container_width=True)

def refresh():
    st.cache_data.clear(); st.rerun()

PAGES={'Dashboard':home,'Kenyan Market':market,'Treasury Bills':tbills,'Bond Pricing':bonds,'Options & Greeks':options,'Yield Curve':curve,'Portfolio':portfolio,'Risk Analysis':risk,'Historical Market Explorer':historical,'Market Intelligence':market_intel,'Risk Intelligence':risk_intel,'Portfolio Intelligence':portfolio_intel,'Research Intelligence':research_intel,'Backtesting':backtest,'Stress Testing':stress,'Financial Reports':reports,'Command Center':command}

with st.sidebar:
    st.title('🇰🇪 Kenya Financial Analytics'); st.caption('Unified Quantitative Finance Platform')
    if st.button('🔄 REFRESH DATA',use_container_width=True): refresh()
    selection=st.radio('Navigation',list(PAGES))
    st.divider(); st.subheader('SYSTEM STATUS'); st.success('Database: ONLINE' if DB.exists() else 'Database: NEW'); st.success(f'Quant Modules: {sum((BASE_DIR/x).exists() for x in ["pricing_engine.py","risk_engine.py","portfolio_engine.py","backtest_engine.py","stress_engine.py"])}/5'); st.success(f'CBK History: {len(cbk_history()):,} records'); st.info('Desktop Mode: ACTIVE')

ensure_db()
try: PAGES[selection]()
except Exception as e: st.error('This module encountered an error.'); st.exception(e)
st.divider(); st.caption('Kenya Financial Analytics | Kenyan Market Focus | Unified Desktop Edition')
