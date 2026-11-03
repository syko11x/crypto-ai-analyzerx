from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional
import httpx, os, io, json, re
from datetime import datetime, timezone, timedelta

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

app = FastAPI(title="Crypto AI Mobile MVP", version="0.1.0")
app.mount("/static", StaticFiles(directory="static"), name="static")

BINANCE = os.getenv("BINANCE_BASE_URL", "https://api.binance.com")
TIMEFRAMES = {"5m", "15m", "1h", "4h", "1d", "1w"}
DEFAULT_PAIRS = [
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT",
    "DOGEUSDT","ADAUSDT","TRXUSDT","AVAXUSDT","LINKUSDT",
    "DOTUSDT","LTCUSDT","BCHUSDT","UNIUSDT","NEARUSDT",
    "APTUSDT","ETCUSDT","ATOMUSDT","FILUSDT","OPUSDT"
]
knowledge_docs = []

@app.get("/")
def home():
    return FileResponse("static/index.html")

@app.get("/api/health")
def health():
    return {"status": "ok", "mode": "paper-trading-only", "server_time": datetime.now(timezone.utc).isoformat()}

@app.get("/api/pairs")
def pairs():
    return {"pairs": DEFAULT_PAIRS, "quote_asset": "USDT"}

@app.get("/api/klines")
async def klines(symbol: str = "BTCUSDT", interval: str = "1h", days: int = 365, limit: int = 1000):
    symbol = symbol.upper()
    if not re.fullmatch(r"[A-Z0-9]{5,20}", symbol):
        raise HTTPException(400, "Invalid symbol")
    if interval not in TIMEFRAMES:
        raise HTTPException(400, "Unsupported timeframe")
    if not 1 <= days <= 365:
        raise HTTPException(400, "days must be 1..365")
    # Binance returns max 1000 klines per request. Paginate backwards to cover the requested period.
    end_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_ms = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)
    rows, cursor = [], end_ms
    async with httpx.AsyncClient(timeout=20) as client:
        while cursor > start_ms and len(rows) < 120000:
            params = {"symbol": symbol, "interval": interval, "endTime": cursor, "limit": min(1000, limit)}
            try:
                r = await client.get(f"{BINANCE}/api/v3/klines", params=params)
                r.raise_for_status()
            except Exception as e:
                raise HTTPException(502, f"Market data request failed: {str(e)[:180]}")
            batch = r.json()
            if not batch:
                break
            rows = batch + rows
            next_cursor = int(batch[0][0]) - 1
            if next_cursor >= cursor:
                break
            cursor = next_cursor
            if len(batch) < 1000:
                break
    rows = [x for x in rows if int(x[0]) >= start_ms]
    return {"symbol": symbol, "interval": interval, "days": days, "count": len(rows),
            "candles": [{"time": int(x[0]), "open": float(x[1]), "high": float(x[2]),
                         "low": float(x[3]), "close": float(x[4]), "volume": float(x[5])} for x in rows]}

@app.post("/api/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Upload a PDF file")
    raw = await file.read()
    if len(raw) > 15 * 1024 * 1024:
        raise HTTPException(413, "PDF must be 15 MB or smaller")
    if PdfReader is None:
        raise HTTPException(500, "Install pypdf to enable PDF extraction")
    try:
        reader = PdfReader(io.BytesIO(raw))
        extracted = "\n".join((p.extract_text() or "") for p in reader.pages)
    except Exception:
        raise HTTPException(400, "Could not read this PDF")
    doc = {"name": file.filename, "pages": len(reader.pages), "characters": len(extracted),
           "text_preview": extracted[:6000]}
    knowledge_docs.append(doc)
    return {"message": "PDF text extracted into this session's knowledge library",
            "document": {k:v for k,v in doc.items() if k != "text_preview"},
            "preview": extracted[:1500],
            "important": "PDF content is reference knowledge, not automatically executable trading rules. Review and enter explicit rules in Strategy Builder."}

class Strategy(BaseModel):
    name: str = "My strategy"
    fast_ema: int = Field(9, ge=2, le=100)
    slow_ema: int = Field(21, ge=3, le=200)
    rsi_period: int = Field(14, ge=2, le=50)
    rsi_long_max: float = Field(65, ge=1, le=100)
    rsi_short_min: float = Field(35, ge=1, le=100)
    stop_pct: float = Field(1.0, gt=0.05, le=10)
    target_pct: float = Field(2.0, gt=0.05, le=30)

def ema(values, period):
    if len(values) < period: return [None] * len(values)
    k = 2 / (period + 1)
    out = [None] * (period - 1)
    current = sum(values[:period]) / period
    out.append(current)
    for value in values[period:]:
        current = value * k + current * (1-k)
        out.append(current)
    return out

def rsi(values, period):
    out = [None] * len(values)
    if len(values) <= period: return out
    gains, losses = [], []
    for i in range(1, period+1):
        d = values[i] - values[i-1]
        gains.append(max(d, 0)); losses.append(max(-d, 0))
    ag, al = sum(gains)/period, sum(losses)/period
    out[period] = 100 if al == 0 else 100 - 100/(1+ag/al)
    for i in range(period+1, len(values)):
        d = values[i] - values[i-1]
        ag = (ag*(period-1)+max(d,0))/period
        al = (al*(period-1)+max(-d,0))/period
        out[i] = 100 if al == 0 else 100 - 100/(1+ag/al)
    return out

def analyze(candles, s: Strategy):
    closes = [c["close"] for c in candles]
    if len(closes) < max(s.slow_ema, s.rsi_period) + 3:
        return {"signal":"INSUFFICIENT_DATA"}
    fast, slow, rv = ema(closes, s.fast_ema), ema(closes, s.slow_ema), rsi(closes, s.rsi_period)
    i = len(closes)-1
    side = "NO TRADE"
    if fast[i] and slow[i] and fast[i] > slow[i] and rv[i] is not None and rv[i] <= s.rsi_long_max:
        side = "LONG"
    elif fast[i] and slow[i] and fast[i] < slow[i] and rv[i] is not None and rv[i] >= s.rsi_short_min:
        side = "SHORT"
    price = closes[i]
    if side == "LONG":
        entry = [price*0.9995, price*1.0005]
        sl, tp = price*(1-s.stop_pct/100), price*(1+s.target_pct/100)
    elif side == "SHORT":
        entry = [price*0.9995, price*1.0005]
        sl, tp = price*(1+s.stop_pct/100), price*(1-s.target_pct/100)
    else:
        entry, sl, tp = None, None, None
    return {"signal": side, "last_close": price, "entry_range": entry, "stop_loss": sl,
            "take_profit": tp, "rsi": rv[i], "fast_ema": fast[i], "slow_ema": slow[i],
            "note": "Rule-based demo signal; not a prediction or guaranteed entry."}

@app.post("/api/analyze")
async def analyze_endpoint(symbol: str = "BTCUSDT", interval: str = "1h", strategy: Strategy = Strategy()):
    data = await klines(symbol, interval, 365, 1000)
    result = analyze(data["candles"], strategy)
    return {"symbol": symbol, "interval": interval, "strategy": strategy.name,
            "candles_used": data["count"], "result": result}

@app.get("/api/knowledge")
def knowledge():
    return {"documents": [{k:v for k,v in d.items() if k != "text_preview"} for d in knowledge_docs],
            "note": "In-memory MVP library resets when the server restarts."}

@app.get("/api/backtest")
async def backtest(symbol: str = "BTCUSDT", interval: str = "1h",
                   fast_ema: int = 9, slow_ema: int = 21,
                   stop_pct: float = 1.0, target_pct: float = 2.0):
    if fast_ema >= slow_ema:
        raise HTTPException(400, "Fast EMA must be smaller than slow EMA")
    data = await klines(symbol, interval, 365, 1000)
    cs = data["candles"]
    closes = [c["close"] for c in cs]
    f, slw = ema(closes, fast_ema), ema(closes, slow_ema)
    trades, wins, losses = 0, 0, 0
    # Simple close-to-close crossover simulation. Conservative: if TP and SL both occur in one candle, count SL first.
    position = None
    for i in range(1, len(cs)):
        if position:
            c = cs[i]
            if position["side"] == "LONG":
                hit_sl, hit_tp = c["low"] <= position["sl"], c["high"] >= position["tp"]
            else:
                hit_sl, hit_tp = c["high"] >= position["sl"], c["low"] <= position["tp"]
            if hit_sl or hit_tp:
                trades += 1
                if hit_tp and not hit_sl: wins += 1
                else: losses += 1
                position = None
        if not position and f[i] and slw[i] and f[i-1] and slw[i-1]:
            if f[i-1] <= slw[i-1] and f[i] > slw[i]:
                p=closes[i]; position={"side":"LONG","sl":p*(1-stop_pct/100),"tp":p*(1+target_pct/100)}
            elif f[i-1] >= slw[i-1] and f[i] < slw[i]:
                p=closes[i]; position={"side":"SHORT","sl":p*(1+stop_pct/100),"tp":p*(1-target_pct/100)}
    return {"symbol":symbol,"interval":interval,"candles":len(cs),"closed_trades":trades,
            "wins":wins,"losses":losses,"win_rate_pct": round(wins/trades*100,2) if trades else None,
            "warning":"Simplified educational backtest; excludes fees, slippage, funding, latency and unclosed positions. Not a reliable forecast."}
