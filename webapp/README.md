# DromX Web

Web application layer over the DromX engine. **Read-only** over the
engine (imports `DromXGraph` etc.; never modifies `dromx/`).

## Architecture

```
webapp/
├── backend/   FastAPI + SSE — drives the engine's graph.stream, streams
│              per-node report sections live, persists runs, serves Q&A
└── frontend/  Vite + React + TS + Tailwind — ZA-Bank-style light UI
```

Runs are persisted as JSON under `~/.dromx/web_runs/<id>.json`
(metadata + the engine's `final_state` = the 14+ markdown report sections).

## Backend

Install web deps into the engine's env, then run uvicorn:

```bash
conda run -n dromx pip install -e ".[web]"   # or: pip install fastapi "uvicorn[standard]" sse-starlette
conda run -n dromx uvicorn webapp.backend.main:app --host 127.0.0.1 --port 8077 --log-level info
```

The backend logs at INFO: a startup banner, and one line per pipeline node as it
completes (`run <id>  ✓ market_report (58s, 2672 chars)`), so a run's progress is
visible in the terminal and failures are easy to trace. (App logging is forced on
regardless of uvicorn's `--log-level`, but passing `info` keeps uvicorn's own
access lines too.)

API:
- `POST /api/runs` — `{ticker, trade_date, analysts[], depth}` → `{id, status}`
- `GET  /api/runs/{id}/stream` — SSE: `start` → `section` (×N, live) → `complete`
- `GET  /api/runs` — history (newest first)
- `GET  /api/runs/{id}` — full stored run (final_state)
- `GET  /api/price/{ticker}?date=&days=` — recent OHLC for the price chart
- `POST /api/runs/{id}/qa` — `{question, history[]}` → `{answer}` (reuses the
  engine's report summarizer + Q&A agent; does NOT re-run the pipeline)
- `POST /api/runs/{id}/qa/stream` — SSE token-by-token Q&A (`delta` → `done`)
- `POST /api/login` — `{password}` → `{token}` (only when auth is enabled)
- `GET  /api/auth/status` — `{auth_required}` (frontend reads this on load)
- `GET  /api/health`

The configured engine (`.env`: provider/keys/holdings/peers/...) is reused as-is;
the API only overrides ticker/date/analysts/depth per run.

### Optional password login

Set `DROMX_WEB_PASSWORD` to require a single shared password. When set,
all `/api/runs*`, `/api/price*` and Q&A routes need a bearer token from
`POST /api/login` (the frontend shows a login page and stores the token). The
token is HMAC-signed with the password and expires after a week — no database,
no user accounts. **Unset (default) = open access**, unchanged local experience.

```bash
DROMX_WEB_PASSWORD=yourpass conda run -n dromx \
  uvicorn webapp.backend.main:app --port 8077 --log-level info
```

## Frontend

```bash
cd webapp/frontend
npm install
npm run dev        # Vite dev server; proxies /api to the backend
```
