# Kenya Financial Analytics

## Kenyan Quantitative Finance & Market Intelligence Platform

A Streamlit-based quantitative-finance platform focused on the Kenyan financial market.

### Live Application
https://kenya-financial-analytics.streamlit.app

### GitHub
https://github.com/paulndwekia/Kenya-Financial-Analytics

### Core Capabilities
- Kenyan market and CBK data analysis
- Foreign exchange analytics
- Treasury Bill analysis
- Yield curve and fixed-income analytics
- Bond pricing
- Options pricing and Greeks
- Portfolio analytics
- Risk analysis and stress testing
- Backtesting and financial research

### Data
The production platform uses official Central Bank of Kenya data for CBK-connected market datasets and maintains historical observations in SQLite databases.

### Technology
Python, Streamlit, Pandas, NumPy, SciPy, Plotly, SQLite, GitHub Actions

### Deployment
The application is deployed through Streamlit Community Cloud and the CBK market-data update pipeline is automated through GitHub Actions.

### Project Status
Production deployment: Live

### Disclaimer
This platform is intended for education, research and quantitative financial analysis. Market information and analytical outputs should be independently verified before financial decisions.

## Vercel + React migration

A new Next.js application is being introduced alongside the retained Streamlit/Python application. The migration branch is `vercel-react-migration`.

### Current migration foundation
- Next.js App Router interface using the Modern Market Terminal palette (light-first, optional dark mode).
- All 16 original workspaces are represented in the navigation.
- A read-only market-data API reads the existing CBK SQLite snapshots without inventing observations.
- Existing Python analytics engines and historical databases remain in the repository while their interfaces are migrated.
- Security response headers, cookie preference controls, privacy notice, cookie notice and terms page are included.

### Deployment and data notes
The API currently reads the checked-in SQLite database snapshots in read-only mode. This is a transition adapter, not a durable multi-writer database. Before the old Streamlit deployment is retired, move persistent market data to a managed PostgreSQL store or another durable database and point the scheduled CBK importer at that store. Keep credentials in Vercel environment variables and GitHub Actions secrets; never commit secrets.

### Important
The React migration is being rolled out in stages. The original Python calculation modules remain the reference implementation. A workspace should only be marked fully migrated after its calculations, inputs, outputs and data provenance have been verified against that implementation.
