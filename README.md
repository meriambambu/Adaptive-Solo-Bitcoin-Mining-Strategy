# Adaptive Bitcoin Solo Mining — Braiins Hash Power Bot

An open-source adaptive bidding bot and real-time dashboard for the [Braiins Hash Power](https://hashpower.braiins.com) marketplace. It automatically adjusts your bid price to stay in the cheapest **top-N** bids in the order book, maximising hashrate received while minimising cost.

> **Order creation is always manual** — the bot only adjusts prices on orders you've already placed. You remain in full control of your budget.

---

## Features

- **Adaptive bidding** — raises price when falling out of top N, lowers it when overpriced
- **Hard price cap** — never bids above your `MAX_BID_PRICE`, protecting your budget
- **Real-time dashboard** — Vue 3 + Tailwind dark UI with live WebSocket updates
- **Order book view** — top-20 bids with your position highlighted in green
- **Strategy log** — full audit trail of every price adjustment decision
- **Always-on scheduler** — APScheduler runs every configurable interval (default: 60s)
- **Manual trigger** — run a strategy evaluation instantly from the dashboard
- **Open source & secure** — credentials live only in `.env`, never logged or committed

---

## Architecture

```
┌─────────────────────────────────────────┐
│            Vue 3 Frontend               │
│  BidsTable · MarketOverview · Strategy  │
│         Panel · CreateBidModal          │
└──────────────┬──────────────────────────┘
               │  HTTP REST + WebSocket
┌──────────────▼──────────────────────────┐
│           FastAPI Backend               │
│  /api/orders  /api/market  /api/settings│
│  /api/strategy   /ws (WebSocket)        │
│  APScheduler → adaptive strategy loop  │
└──────────────┬──────────────────────────┘
               │  HMAC-SHA256 signed requests
┌──────────────▼──────────────────────────┐
│     Braiins Hash Power REST API         │
│   hashpower.braiins.com/api/v2/…        │
└─────────────────────────────────────────┘
          │
     SQLite DB (strategy logs + snapshots)
```

---

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- A Braiins Hash Power account with API keys

### 1 — Clone & configure

```bash
git clone https://github.com/your-username/adaptive-bitcoin-mining.git
cd adaptive-bitcoin-mining

# Copy and fill in your credentials
cp backend/.env.example backend/.env
```

Edit `backend/.env` — see [Configuration](#configuration) below.

### 2 — Start the backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend runs at `http://localhost:8000`. Swagger docs at `http://localhost:8000/docs`.

### 3 — Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard opens at `http://localhost:5173`.

---

## Configuration

All settings live in `backend/.env` (never committed). Copy from `backend/.env.example`.

### Getting Your API Key

1. Log in to [hashpower.braiins.com](https://hashpower.braiins.com)
2. Go to **Account → Settings → API Keys → Generate New Key**
3. Copy the single API key value into `BRAIINS_API_KEY` in `backend/.env`
4. If you get 401 errors, open `hashpower.braiins.com/api/` → Authorize → run a test request → check the Network tab to confirm the exact header name

### Strategy Parameters

| Variable | Default | Description |
|---|---|---|
| `TOP_N` | `5` | Stay in the cheapest N bids in the order book |
| `MAX_BID_PRICE` | `0.60` | Hard ceiling — never bid above this (BTC/EH/day) |
| `MIN_BID_PRICE` | `0.10` | Floor — never bid below this |
| `UPPER_BUFFER` | `0.01` | Gap above P_N before lowering (prevents flapping) |
| `LOWER_MARGIN` | `0.005` | How far below P_N to target when lowering |
| `PRICE_STEP` | `0.005` | Increment when raising price |
| `POLL_INTERVAL` | `60` | Seconds between cycles (minimum 30) |
| `STRATEGY_ENABLED` | `true` | Master on/off switch |

All parameters are also editable live from the **Strategy Settings** panel in the dashboard without restarting.

### Pool Setup

For Braiins Solo mining, use:

```
Pool URL:  public.stratum.braiins.com
Port:      3333
Username:  your_bitcoin_address.worker_name
```

---

## How the Strategy Works

```
Every POLL_INTERVAL seconds:

1. Fetch your active orders from Braiins API
   └─ If none → log IDLE, skip (no auto-create)

2. Fetch public order book, sort by price ASC

3. Find P_N = price of the Nth cheapest bid

4. For each active order:
   ┌─ my_price > MAX_BID_PRICE?
   │  └─ LOWER to MAX_BID_PRICE (hard cap)
   ├─ my_price > P_N + UPPER_BUFFER?
   │  └─ LOWER to max(P_N − LOWER_MARGIN, MIN_BID_PRICE)
   ├─ my_price < P_N?
   │  └─ RAISE to min(P_N + PRICE_STEP, MAX_BID_PRICE)
   └─ otherwise → HOLD (already competitive)

5. Log decision → SQLite
6. Broadcast to all dashboard WebSocket clients
```

### What the bot does NOT do

- **Does not create orders** — use the dashboard's **+ Create** button
- **Does not cancel orders** — use the dashboard's cancel (×) button
- **Does not manage budget** — you set the BTC amount when creating an order
- **Does not raise beyond MAX_BID_PRICE** — ever

---

## Dashboard

| Panel | Description |
|---|---|
| **Current Bids** | Live table of your orders: price, budget, speed, ETA, progress ring |
| **Order Book** | Top-20 public bids; top-N highlighted green, your P_N shown |
| **Strategy Settings** | Edit all parameters live; enable/disable; manual trigger |
| **Strategy Log** | Timestamped log of every RAISE / LOWER / HOLD / IDLE decision |
| **Balance Bar** | Available BTC, total balance, pending |
| **WS indicator** | Green "Live" / red "Connecting" dot in header |

---

## Local API Reference

| Method | Path | Description |
|---|---|---|
| GET | `/api/orders` | List your orders |
| POST | `/api/orders` | Create a new order |
| PUT | `/api/orders/{id}` | Update price/budget/speed |
| DELETE | `/api/orders/{id}` | Cancel order |
| GET | `/api/market/orderbook` | Public order book |
| GET | `/api/market/balance` | Your BTC balance |
| GET | `/api/settings` | Current strategy settings |
| PATCH | `/api/settings` | Update strategy settings live |
| POST | `/api/strategy/evaluate` | Manual strategy cycle trigger |
| GET | `/api/strategy/logs` | Strategy decision log |
| WS | `/ws` | Real-time push updates |

---

## Security

### Protecting Your API Keys

- **Never commit `.env`** — it is listed in `.gitignore` by default
- The backend never logs your `BRAIINS_API_KEY_ID`, `BRAIINS_API_SECRET`, or `BRAIINS_ORG_ID`
- API credentials are only used server-side; the frontend never receives them
- Use `.env.example` as a template — it contains only placeholder values

### Open Source Contributor Notes

If you fork or contribute to this project:

1. Check `git status` before pushing — ensure `.env` is not staged
2. Never hardcode credentials, wallet addresses, or pool passwords in source files
3. The `Settings.safe_dict()` method exists for logging — use it, never `Settings.model_dump()`
4. Run `git secret` or `trufflehog` on your branch before opening a PR

---

## Troubleshooting

**Backend fails to start with "Replace BRAIINS_API_KEY placeholder"**
→ Open `backend/.env` and set `BRAIINS_API_KEY` to your actual key from the Braiins dashboard.

**Strategy runs but prices never change**
→ Confirm `STRATEGY_ENABLED=true` in `.env` and check the Strategy Log panel for `IDLE` entries (means no active orders).

**Order updates fail with 401/403**
→ Open `hashpower.braiins.com/api/` in a browser, click Authorize, paste your key, execute a request, and check the Network tab. If the header is `X-Api-Key` instead of `Authorization: Bearer`, update `_auth_headers()` in [backend/app/braiins/client.py](backend/app/braiins/client.py).

**WebSocket shows "Connecting…"**
→ Ensure the backend is running on port 8000. The Vite dev proxy handles `/ws` automatically in development.

---

## License

MIT — see [LICENSE](LICENSE).
