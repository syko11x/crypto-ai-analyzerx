# Crypto AI Scanner — Mobile MVP

A mobile-first, installable-web-app starter for **research and paper trading only**.

## Included
- Mobile-responsive dashboard / PWA manifest
- 20-symbol USDT watchlist
- Binance public spot kline history API (1-year lookback; supported intervals: 5m, 15m, 1h, 4h, 1d, 1w)
- Rule-based EMA + RSI example signal
- Simplified historical EMA crossover backtest
- PDF text extraction for your own strategy reference library
- No API keys, exchange account, or trading permissions required

## Important limitations
- This is a starter MVP, not a validated profitable trading system.
- It does **not** place orders or connect to private exchange accounts.
- Win rate is historical and can be misleading. The sample backtest excludes fees, slippage, funding, latency, and open trades.
- A PDF is stored as reference text; it does not automatically become executable strategy logic. You must review it and explicitly encode rules.
- The initial 20 pairs are a starter watchlist, not a live top-20-by-volume ranking.
- The PDF library is in memory and resets when the server restarts.
- A PWA needs HTTPS to install on most phones. Browser notifications and background execution have platform limits.
- Free hosting tiers may sleep, impose usage caps, or change pricing. Guaranteed 24/7 background monitoring is generally not free.

## Run locally
Python 3.10+ recommended.

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Open http://127.0.0.1:8000 on your phone and computer on the same Wi-Fi using your computer's LAN IP, or deploy to a host that supports Python ASGI apps and HTTPS.

## Next production steps
1. Add persistent database and object storage for PDFs / strategies.
2. Add scheduled cloud jobs and WebSocket market streams.
3. Build complete candle pagination and caching per pair/timeframe.
4. Add realistic fee/slippage/funding simulation and out-of-sample walk-forward testing.
5. Add ranking only after enough completed, validated paper trades.
6. Add web-push notification subscription and service worker.
7. Add rule editor for S/R, FVG, Fibonacci and SMC concepts with user approval and test cases.
8. Add server-side authentication and per-user data isolation.

## API
- `GET /api/health`
- `GET /api/pairs`
- `GET /api/klines?symbol=BTCUSDT&interval=1h&days=365`
- `POST /api/analyze?symbol=BTCUSDT&interval=1h` (JSON strategy body)
- `GET /api/backtest?symbol=BTCUSDT&interval=1h`
- `POST /api/upload-pdf` (multipart PDF)
- `GET /api/knowledge`

## Android installation (PWA)
1. Deploy this project to a Python ASGI host that provides HTTPS.
2. Open the deployed HTTPS address in Chrome on Android.
3. Use Chrome's menu → **Install app** (or **Add to Home screen**, depending on Chrome version).
4. Launch **Crypto AI Analyzer** from the Android home screen.

The service worker caches the app shell for quicker repeat visits. API requests still need an internet connection. This project is a PWA, not a signed APK; an APK would be a separate packaging step.
