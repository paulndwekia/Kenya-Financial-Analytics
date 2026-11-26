# Kenya Financial Analytics

A Kenyan quantitative-finance and market-intelligence research terminal for exploring official market observations and applying practical financial models.

## Application

- **Framework:** Next.js and React
- **Hosting:** Vercel
- **Database:** Neon PostgreSQL
- **Market-data source:** Central Bank of Kenya (CBK)
- **Status:** Completed application

The interface brings sixteen focused workspaces into one responsive research environment.

## Workspaces

| Workspace | What it covers |
|---|---|
| Dashboard | Data-service status, latest FX observations and the current matched Treasury-bill curve |
| Kenyan Market | Historical currency-pair observations, returns and drawdown |
| Market Intelligence | Comparative FX performance and realised volatility |
| Yield Curve | Treasury-bill curve construction, tenor spreads and interpolation |
| Treasury Bills | Auction history, tenor analysis and investment-yield price calculations |
| Bond Pricing | Coupon-bond valuation, yield, duration, convexity and cash-flow schedules |
| Options & Greeks | European option valuation and Black–Scholes sensitivities |
| Backtesting | Moving-average strategy research with lagged signals and trading costs |
| Risk Analysis | Value at Risk, expected shortfall and drawdown |
| Risk Intelligence | Treasury-auction yield dispersion by tenor |
| Stress Testing | Capital and duration/convexity rate-shock scenarios |
| Portfolio Intelligence | Cross-currency returns, correlations and risk-return comparisons |
| Portfolio | Weighted currency basket using aligned observations |
| Historical Market Explorer | Filterable historical observations and data export |
| Research Intelligence | Moving-average trend research |
| Financial Reports | Source-aware market and auction reporting |

## Data architecture

Persistent market observations are stored in Neon PostgreSQL.

- `fx_observations` stores dated FX observations by currency pair.
- `treasury_bill_observations` stores auction observations by date and tenor.
- `data_refresh_runs` records the outcome and audit details of each market-data refresh.

The public market API reads stored observations and reports database availability. It does not invent values to fill missing dates. Observations retain their CBK source attribution.

## Automated CBK refresh

The protected Vercel function `/api/refresh` imports current FX and Treasury-bill observations from official CBK pages and auction-result PDFs. It is scheduled for weekdays at 15:15 UTC (18:15 Nairobi time).

The importer uses the sensitive Vercel environment variables `DATABASE_URL` and `CRON_SECRET`. Refresh outcomes are recorded in `data_refresh_runs`, including partial and failed attempts. The function is bounded to a small number of recent auction-result PDFs per run.

## Application endpoints

- `/api/market` — read-only market data and service health.
- `/api/refresh` — authenticated market-data ingestion.
- `/api/report` — financial report generation.

## Security and privacy

- Database credentials and refresh authorisation are stored as sensitive Vercel environment variables.
- The public market endpoint is read-only.
- The ingestion endpoint requires bearer-token authorisation.
- Response headers include frame protection, MIME-sniffing protection, referrer policy and permissions policy.
- Privacy, terms and cookie notices are available in the application.
- The browser stores only essential preferences such as theme and cookie choice.

## Local development

Use Node.js 24 and Python 3.12.

```bash
npm install
npm run dev
```

The Next.js application uses React, Recharts, Motion and Lucide. Python dependencies for the hosted API functions are listed in `requirements.txt`.

## Quality checks

```bash
npm test
npm run lint
npm run test:e2e
```

The automated finance tests cover Treasury-bill conventions, bond valuation and cash flows, option pricing, risk measures, yield-curve calculations, portfolio metrics and workspace registration. The browser acceptance suite checks module navigation and workspace behaviour.

## Disclaimer

Kenya Financial Analytics is intended for education, research and quantitative analysis. It is not investment, legal, tax or accounting advice. Verify market information with its original publisher before relying on it.
