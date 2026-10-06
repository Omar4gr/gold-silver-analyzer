import os
import sqlite3
import time
from typing import Optional
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

DB_PATH = os.getenv("MILA_BRIDGE_DB", "mila_bridge.db")
TOKEN = os.getenv("MILA_BRIDGE_TOKEN", "")
LIVE_TRADING = os.getenv("LIVE_TRADING", "false").lower() == "true"
MAX_LOT = float(os.getenv("MAX_LOT", "1.0"))
ALLOWED_SYMBOL = os.getenv("ALLOWED_SYMBOL", "XAUUSD")

app = FastAPI(title="MILA Remote MT5 Bridge", version="1.0.0")

def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS signals(
        id INTEGER PRIMARY KEY AUTOINCREMENT, signal_id TEXT UNIQUE NOT NULL,
        symbol TEXT NOT NULL, side TEXT NOT NULL, volume REAL NOT NULL,
        entry REAL NOT NULL, sl REAL NOT NULL, tp REAL NOT NULL,
        timeframe TEXT, signal_name TEXT, status TEXT NOT NULL,
        created REAL NOT NULL, result TEXT)""")
    c.commit()
    return c

class Signal(BaseModel):
    signal_id: str
    symbol: str
    side: str
    volume: float = Field(gt=0)
    entry: float
    sl: float
    tp: float
    timeframe: str = ""
    signal_name: str = ""

def auth(token: Optional[str]):
    if not TOKEN or token != TOKEN:
        raise HTTPException(401, "Invalid bridge token")

def validate(s: Signal):
    if s.symbol != ALLOWED_SYMBOL:
        raise HTTPException(400, f"Symbol not allowed: {s.symbol}")
    if s.side not in ("BUY", "SELL"):
        raise HTTPException(400, "side must be BUY or SELL")
    if s.volume > MAX_LOT:
        raise HTTPException(400, "volume exceeds MAX_LOT")
    if s.side == "BUY" and not (s.sl < s.entry < s.tp):
        raise HTTPException(400, "BUY requires SL < entry < TP")
    if s.side == "SELL" and not (s.tp < s.entry < s.sl):
        raise HTTPException(400, "SELL requires TP < entry < SL")

@app.get("/health")
def health(x_bridge_token: Optional[str] = Header(default=None)):
    auth(x_bridge_token)
    return {"ok": True, "message": "MILA Bridge is online", "live_trading": LIVE_TRADING}

@app.post("/signal")
def signal(s: Signal, x_bridge_token: Optional[str] = Header(default=None)):
    auth(x_bridge_token)
    validate(s)
    c = db()
    try:
        c.execute("""INSERT INTO signals
        (signal_id,symbol,side,volume,entry,sl,tp,timeframe,signal_name,status,created)
        VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (s.signal_id,s.symbol,s.side,s.volume,s.entry,s.sl,s.tp,s.timeframe,s.signal_name,"queued",time.time()))
        c.commit()
        return {"accepted": True, "message": "Signal queued", "signal_id": s.signal_id}
    except sqlite3.IntegrityError:
        return {"accepted": True, "message": "Duplicate signal ignored", "signal_id": s.signal_id}
    finally:
        c.close()

@app.get("/command")
def command(x_bridge_token: Optional[str] = Header(default=None)):
    auth(x_bridge_token)
    c = db()
    row = c.execute("SELECT * FROM signals WHERE status='queued' ORDER BY id LIMIT 1").fetchone()
    if row:
        c.execute("UPDATE signals SET status='in_flight' WHERE id=?", (row["id"],))
        c.commit()
    c.close()
    return dict(row) if row else {"command": None}

@app.post("/result")
def result(signal_id: str, status: str, result: str = "", x_bridge_token: Optional[str] = Header(default=None)):
    auth(x_bridge_token)
    c = db()
    c.execute("UPDATE signals SET status=?,result=? WHERE signal_id=?", (status,result,signal_id))
    c.commit()
    c.close()
    return {"ok": True}

@app.get("/status")
def status(x_bridge_token: Optional[str] = Header(default=None)):
    auth(x_bridge_token)
    c = db()
    rows = c.execute("SELECT * FROM signals ORDER BY id DESC LIMIT 20").fetchall()
    c.close()
    return {"items": [dict(r) for r in rows]}
