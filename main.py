import os
import uuid
import datetime
import requests
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

try:
    import yfinance as yf
except ImportError:
    yf = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# ============================================================
# 1) PAGE / GLOBAL SETTINGS
# ============================================================
st.set_page_config(
    page_title="MILA Gold & Silver PRO",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
:root {
    --bg: #071018;
    --card: #0d1822;
    --card2: #101f2c;
    --line: rgba(255,255,255,.09);
    --text: #edf5ff;
    --muted: #91a4b7;
    --green: #20d39b;
    --red: #ff5c6c;
    --gold: #e7c56a;
}
html, body, [class*="css"] {
    font-family: Arial, sans-serif;
}
.stApp {
    background:
        radial-gradient(circle at 20% 0%, rgba(231,197,106,.07), transparent 30%),
        radial-gradient(circle at 90% 10%, rgba(32,211,155,.06), transparent 25%),
        var(--bg);
    color: var(--text);
}
.block-container {
    max-width: 1450px;
    padding-top: 1rem;
    padding-bottom: 2rem;
}
.hero {
    padding: 20px 22px;
    border: 1px solid var(--line);
    border-radius: 20px;
    background: linear-gradient(135deg, rgba(231,197,106,.10), rgba(13,24,34,.96));
    box-shadow: 0 12px 35px rgba(0,0,0,.20);
    margin-bottom: 14px;
}
.hero h1 { margin: 0; font-size: 30px; }
.hero p { margin: 7px 0 0; color: var(--muted); }
.card {
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 16px;
    background: rgba(13,24,34,.82);
    box-shadow: 0 8px 25px rgba(0,0,0,.13);
}
.signal-buy {
    border: 1px solid rgba(32,211,155,.45);
    background: rgba(32,211,155,.08);
    border-radius: 18px;
    padding: 18px;
}
.signal-sell {
    border: 1px solid rgba(255,92,108,.45);
    background: rgba(255,92,108,.08);
    border-radius: 18px;
    padding: 18px;
}
.signal-neutral {
    border: 1px solid rgba(231,197,106,.30);
    background: rgba(231,197,106,.06);
    border-radius: 18px;
    padding: 18px;
}
.small-muted { color: var(--muted); font-size: 13px; }
.metric {
    padding: 13px;
    border-radius: 14px;
    background: rgba(255,255,255,.035);
    border: 1px solid var(--line);
}
@media (max-width: 700px) {
    .block-container { padding: .55rem .55rem 1.2rem; }
    .hero { padding: 15px; border-radius: 15px; }
    .hero h1 { font-size: 22px; }
    .hero p { font-size: 12px; }
    .card { padding: 12px; border-radius: 13px; }
    [data-testid="stMetricValue"] { font-size: 20px; }
    [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap;
    }
    [data-testid="column"] {
        min-width: 47% !important;
    }
}
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# 2) AI / GROQ
# ============================================================
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY", ""))

client = None
if GROQ_API_KEY and OpenAI:
    try:
        client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=GROQ_API_KEY,
        )
    except Exception:
        client = None


# ============================================================
# 3) MARKET HOURS
# ============================================================
def check_market_status():
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    iraq_now = utc_now + datetime.timedelta(hours=3)
    weekday = iraq_now.weekday()
    hour = iraq_now.hour

    if weekday == 5:
        return False, "السوق مغلق — عطلة نهاية الأسبوع 🔴", "يفتح يوم الإثنين"
    if weekday == 6:
        return False, "السوق مغلق — عطلة نهاية الأسبوع 🔴", "يفتح يوم الإثنين"
    if weekday == 0 and hour < 1:
        return False, "السوق مغلق وقارب على الافتتاح ⏳", "يفتح اليوم الساعة 1:00 فجراً"
    return True, "السوق مفتوح 🟢", ""


market_open, market_status_text, market_reopen = check_market_status()


# ============================================================
# 4) DATA
# ============================================================
def normalize_symbol(symbol):
    s = (symbol or "").upper().strip()
    if s in ("XAUUSD", "GOLD", "GC"):
        return "XAUUSD"
    if s in ("XAGUSD", "SILVER", "SI"):
        return "XAGUSD"
    return s


def yahoo_symbol(symbol):
    symbol = normalize_symbol(symbol)
    if symbol == "XAUUSD":
        return "GC=F"
    if symbol == "XAGUSD":
        return "SI=F"
    return symbol


def fetch_market_data(symbol="XAUUSD", interval="5m", period="5d"):
    if yf is None:
        return pd.DataFrame()

    ticker = yahoo_symbol(symbol)
    try:
        df = yf.download(
            ticker,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=False,
            threads=False,
        )
        if df is None or df.empty:
            return pd.DataFrame()

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]

        df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]

        needed = ["open", "high", "low", "close", "volume"]
        for col in needed:
            if col not in df.columns:
                if col == "volume":
                    df[col] = 0
                else:
                    return pd.DataFrame()

        df = df[needed].copy()
        df = df.dropna(subset=["open", "high", "low", "close"])
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0)
        return df
    except Exception:
        return pd.DataFrame()


# ============================================================
# 5) INDICATORS
# ============================================================
def ema(series, length):
    return series.ewm(span=length, adjust=False).mean()


def rsi(series, length=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / length, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def atr(df, length=14):
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / length, adjust=False).mean()


def enrich_indicators(df):
    df = df.copy()
    df["ema21"] = ema(df["close"], 21)
    df["ema50"] = ema(df["close"], 50)
    df["ema200"] = ema(df["close"], 200)
    df["rsi"] = rsi(df["close"], 14)
    df["atr"] = atr(df, 14)
    df["vol_ma"] = df["volume"].rolling(20).mean()
    df["body"] = (df["close"] - df["open"]).abs()
    df["range"] = (df["high"] - df["low"]).replace(0, np.nan)
    df["body_ratio"] = df["body"] / df["range"]
    return df


# ============================================================
# 6) VOLUME PROFILE
# ============================================================
def calc_volume_profile(df, rows=30, lookback=120, va_pct=70):
    data = df.tail(lookback).copy()
    if data.empty:
        return {
            "poc": np.nan,
            "vah": np.nan,
            "val": np.nan,
            "bins": np.array([]),
            "volumes": np.array([]),
        }

    low = float(data["low"].min())
    high = float(data["high"].max())

    if not np.isfinite(low) or not np.isfinite(high):
        return {
            "poc": np.nan, "vah": np.nan, "val": np.nan,
            "bins": np.array([]), "volumes": np.array([])
        }

    if high <= low:
        high = low + 0.01

    edges = np.linspace(low, high, rows + 1)
    volumes = np.zeros(rows)

    for _, row in data.iterrows():
        price = float((row["high"] + row["low"] + row["close"]) / 3)
        vol = float(row["volume"]) if np.isfinite(row["volume"]) else 0.0
        idx = np.searchsorted(edges, price, side="right") - 1
        idx = max(0, min(rows - 1, idx))
        volumes[idx] += max(vol, 1.0)

    centers = (edges[:-1] + edges[1:]) / 2
    poc_idx = int(np.argmax(volumes))
    poc = float(centers[poc_idx])

    total = volumes.sum()
    target = total * (va_pct / 100.0)

    selected = {poc_idx}
    accumulated = volumes[poc_idx]
    left = poc_idx - 1
    right = poc_idx + 1

    while accumulated < target and (left >= 0 or right < rows):
        lv = volumes[left] if left >= 0 else -1
        rv = volumes[right] if right < rows else -1

        if rv >= lv:
            if right < rows:
                selected.add(right)
                accumulated += volumes[right]
                right += 1
            elif left >= 0:
                selected.add(left)
                accumulated += volumes[left]
                left -= 1
        else:
            if left >= 0:
                selected.add(left)
                accumulated += volumes[left]
                left -= 1
            elif right < rows:
                selected.add(right)
                accumulated += volumes[right]
                right += 1

    val = float(edges[min(selected)])
    vah = float(edges[max(selected) + 1])

    return {
        "poc": poc,
        "vah": vah,
        "val": val,
        "bins": centers,
        "volumes": volumes,
    }


# ============================================================
# 7) MILA ANALYZER
# ============================================================
def analyze_mila(
    df,
    profile_rows=30,
    lookback=120,
    va_pct=70,
    volume_multiplier=1.2,
    rr=1.5,
    sweep_len=20,
    piv_len=5,
    zone_atr=0.3,
):
    if df is None or len(df) < 60:
        return {
            "signal": "WAIT",
            "reason": "بيانات غير كافية للتحليل.",
            "score": 0,
            "entry": np.nan,
            "sl": np.nan,
            "tp": np.nan,
            "poc": np.nan,
            "vah": np.nan,
            "val": np.nan,
            "trend": "غير معروف",
            "rsi": np.nan,
            "atr": np.nan,
            "volume_ratio": np.nan,
            "confirmations": [],
        }

    d = enrich_indicators(df)
    p = calc_volume_profile(d, profile_rows, lookback, va_pct)

    last = d.iloc[-1]
    prev = d.iloc[-2]

    close = float(last["close"])
    atr_v = float(last["atr"]) if np.isfinite(last["atr"]) else 0.0
    rsi_v = float(last["rsi"]) if np.isfinite(last["rsi"]) else 50.0

    vol_ma = float(last["vol_ma"]) if np.isfinite(last["vol_ma"]) else 0.0
    volume_ratio = float(last["volume"] / vol_ma) if vol_ma > 0 else 1.0

    ema21 = float(last["ema21"])
    ema50 = float(last["ema50"])
    ema200 = float(last["ema200"])

    if close > ema21 > ema50 > ema200:
        trend = "صاعد قوي 🟢"
        trend_bias = 1
    elif close < ema21 < ema50 < ema200:
        trend = "هابط قوي 🔴"
        trend_bias = -1
    elif close > ema50:
        trend = "صاعد"
        trend_bias = 1
    elif close < ema50:
        trend = "هابط"
        trend_bias = -1
    else:
        trend = "جانبي"
        trend_bias = 0

    recent_high = float(d["high"].tail(sweep_len + 1).iloc[:-1].max())
    recent_low = float(d["low"].tail(sweep_len + 1).iloc[:-1].min())

    bullish_candle = close > float(last["open"])
    bearish_candle = close < float(last["open"])

    bullish_reclaim = close > float(prev["high"]) and bullish_candle
    bearish_reclaim = close < float(prev["low"]) and bearish_candle

    sweep_low = (
        float(last["low"]) < recent_low
        and close > recent_low
    )
    sweep_high = (
        float(last["high"]) > recent_high
        and close < recent_high
    )

    zone = max(atr_v * zone_atr, 0.01)

    near_val = np.isfinite(p["val"]) and abs(close - p["val"]) <= zone
    near_vah = np.isfinite(p["vah"]) and abs(close - p["vah"]) <= zone
    near_poc = np.isfinite(p["poc"]) and abs(close - p["poc"]) <= zone

    breakout_up = np.isfinite(p["vah"]) and close > p["vah"] and float(prev["close"]) <= p["vah"]
    breakout_down = np.isfinite(p["val"]) and close < p["val"] and float(prev["close"]) >= p["val"]

    volume_ok = volume_ratio >= volume_multiplier

    buy_score = 0
    sell_score = 0
    buy_reasons = []
    sell_reasons = []

    if trend_bias > 0:
        buy_score += 2
        buy_reasons.append("اتجاه صاعد")
    elif trend_bias < 0:
        sell_score += 2
        sell_reasons.append("اتجاه هابط")

    if sweep_low:
        buy_score += 2
        buy_reasons.append("Liquidity Sweep أسفل")
    if sweep_high:
        sell_score += 2
        sell_reasons.append("Liquidity Sweep أعلى")

    if bullish_reclaim:
        buy_score += 1
        buy_reasons.append("استعادة قمة الشمعة السابقة")
    if bearish_reclaim:
        sell_score += 1
        sell_reasons.append("كسر قاع الشمعة السابقة")

    if near_val:
        buy_score += 2
        buy_reasons.append("قرب VAL")
    if near_vah:
        sell_score += 2
        sell_reasons.append("قرب VAH")

    if breakout_up:
        buy_score += 2
        buy_reasons.append("Breakout VAH")
    if breakout_down:
        sell_score += 2
        sell_reasons.append("Breakdown VAL")

    if volume_ok:
        if buy_score > sell_score:
            buy_score += 1
            buy_reasons.append("حجم مؤكد")
        elif sell_score > buy_score:
            sell_score += 1
            sell_reasons.append("حجم مؤكد")

    if rsi_v < 35:
        buy_score += 1
        buy_reasons.append("RSI منخفض")
    elif rsi_v > 65:
        sell_score += 1
        sell_reasons.append("RSI مرتفع")

    signal = "WAIT"
    reasons = []
    entry = close
    sl = np.nan
    tp = np.nan

    threshold = 5

    if buy_score >= threshold and buy_score > sell_score:
        signal = "BUY"
        reasons = buy_reasons
        risk = max(atr_v * 0.5, 0.01)
        sl = close - risk
        tp = close + risk * rr
    elif sell_score >= threshold and sell_score > buy_score:
        signal = "SELL"
        reasons = sell_reasons
        risk = max(atr_v * 0.5, 0.01)
        sl = close + risk
        tp = close - risk * rr
    else:
        if buy_score > sell_score:
            reasons = buy_reasons
        elif sell_score > buy_score:
            reasons = sell_reasons
        else:
            reasons = ["لا توجد أفضلية واضحة حالياً"]

    score = max(buy_score, sell_score)

    return {
        "signal": signal,
        "reason": " • ".join(reasons),
        "score": int(score),
        "buy_score": int(buy_score),
        "sell_score": int(sell_score),
        "entry": float(entry),
        "sl": float(sl) if np.isfinite(sl) else np.nan,
        "tp": float(tp) if np.isfinite(tp) else np.nan,
        "poc": float(p["poc"]),
        "vah": float(p["vah"]),
        "val": float(p["val"]),
        "trend": trend,
        "rsi": rsi_v,
        "atr": atr_v,
        "volume_ratio": volume_ratio,
        "ema21": ema21,
        "ema50": ema50,
        "ema200": ema200,
        "confirmations": reasons,
    }


# ============================================================
# 8) REMOTE MT5 BRIDGE
# ============================================================
def normalize_bridge_url(url):
    return (url or "").strip().rstrip("/")


def check_remote_bridge(base_url, token=""):
    base_url = normalize_bridge_url(base_url)
    if not base_url:
        return False, "رابط Bridge غير موجود."

    headers = {"X-Bridge-Token": token} if token else {}

    try:
        response = requests.get(
            f"{base_url}/health",
            headers=headers,
            timeout=8,
        )
        try:
            data = response.json()
        except ValueError:
            data = response.text

        if response.ok:
            return True, data
        return False, f"HTTP {response.status_code}: {data}"
    except requests.RequestException as exc:
        return False, f"تعذر الاتصال: {exc}"


def send_remote_signal(
    base_url,
    token,
    symbol,
    side,
    volume,
    entry,
    sl,
    tp,
    signal_id,
):
    base_url = normalize_bridge_url(base_url)

    if not base_url:
        return False, "أدخل Bridge API URL."
    if not token:
        return False, "أدخل Bridge Token."
    if side not in {"BUY", "SELL"}:
        return False, "نوع الصفقة يجب أن يكون BUY أو SELL."
    if volume <= 0:
        return False, "Lot غير صالح."

    if side == "BUY" and not (sl < entry < tp):
        return False, "BUY يجب أن يكون SL < Entry < TP."
    if side == "SELL" and not (tp < entry < sl):
        return False, "SELL يجب أن يكون TP < Entry < SL."

    payload = {
        "signal_id": signal_id,
        "symbol": symbol.strip(),
        "side": side,
        "volume": float(volume),
        "entry": float(entry),
        "sl": float(sl),
        "tp": float(tp),
    }

    try:
        response = requests.post(
            f"{base_url}/signal",
            json=payload,
            headers={"X-Bridge-Token": token},
            timeout=12,
        )
        try:
            result = response.json()
        except ValueError:
            result = response.text

        if response.ok:
            return True, result
        return False, f"HTTP {response.status_code}: {result}"
    except requests.RequestException as exc:
        return False, f"تعذر إرسال الإشارة: {exc}"


def fetch_bridge_status(base_url, token=""):
    base_url = normalize_bridge_url(base_url)
    if not base_url:
        return None

    try:
        response = requests.get(
            f"{base_url}/status",
            headers={"X-Bridge-Token": token},
            timeout=8,
        )
        if response.ok:
            return response.json()
    except Exception:
        pass
    return None


# ============================================================
# 9) SIDEBAR SETTINGS
# ============================================================
with st.sidebar:
    st.header("⚙️ إعدادات MILA PRO")

    symbol = st.selectbox(
        "السوق",
        ["XAUUSD", "XAGUSD"],
        index=0,
    )

    interval = st.selectbox(
        "الفريم",
        ["1m", "5m", "15m", "30m", "1h", "4h"],
        index=1,
    )

    period_map = {
        "1m": "5d",
        "5m": "30d",
        "15m": "60d",
        "30m": "60d",
        "1h": "730d",
        "4h": "730d",
    }
    period = period_map[interval]

    profile_rows = st.slider("Profile Rows", 10, 80, 30)
    lookback = st.slider("Profile Lookback", 50, 300, 120)
    va_pct = st.slider("Value Area %", 50, 90, 70)
    volume_multiplier = st.slider("Volume Multiplier", 1.0, 3.0, 1.2, 0.1)
    rr = st.slider("Risk / Reward", 1.0, 5.0, 1.5, 0.1)

    st.markdown("---")
    st.subheader("🌐 Remote MT5")

    bridge_url = st.text_input(
        "Bridge API URL",
        value=os.getenv("MILA_BRIDGE_URL", ""),
        placeholder="https://your-vps-domain.com",
    )

    bridge_token = st.text_input(
        "Bridge Token",
        value=os.getenv("MILA_BRIDGE_TOKEN", ""),
        type="password",
    )

    remote_symbol = st.text_input(
        "رمز MT5",
        value="XAUUSD" if symbol == "XAUUSD" else "XAGUSD",
    )

    remote_volume = st.number_input(
        "Lot",
        min_value=0.01,
        max_value=100.0,
        value=0.01,
        step=0.01,
    )

    remote_enabled = st.checkbox("تفعيل Remote MT5", value=False)
    auto_remote = st.checkbox(
        "إرسال الإشارة تلقائياً",
        value=False,
        help="سيتم إرسال BUY/SELL فقط عندما يعطي MILA إشارة مؤكدة.",
    )

    if st.button("🔎 فحص Bridge", use_container_width=True):
        ok, result = check_remote_bridge(bridge_url, bridge_token)
        if ok:
            st.success("Bridge متصل")
            st.json(result)
        else:
            st.error(result)

    bridge_status = fetch_bridge_status(bridge_url, bridge_token) if remote_enabled else None


# ============================================================
# 10) LOAD + ANALYZE
# ============================================================
with st.spinner("جاري تحميل بيانات السوق وتحليل MILA..."):
    df = fetch_market_data(symbol, interval, period)

if not df.empty:
    analysis = analyze_mila(
        df,
        profile_rows=profile_rows,
        lookback=lookback,
        va_pct=va_pct,
        volume_multiplier=volume_multiplier,
        rr=rr,
    )
else:
    analysis = {
        "signal": "WAIT",
        "reason": "تعذر تحميل بيانات السوق.",
        "score": 0,
        "buy_score": 0,
        "sell_score": 0,
        "entry": np.nan,
        "sl": np.nan,
        "tp": np.nan,
        "poc": np.nan,
        "vah": np.nan,
        "val": np.nan,
        "trend": "غير متاح",
        "rsi": np.nan,
        "atr": np.nan,
        "volume_ratio": np.nan,
        "ema21": np.nan,
        "ema50": np.nan,
        "ema200": np.nan,
        "confirmations": [],
    }


# ============================================================
# 11) AUTO REMOTE SIGNAL
# ============================================================
if "last_auto_signal" not in st.session_state:
    st.session_state.last_auto_signal = ""

if remote_enabled and auto_remote and analysis["signal"] in ("BUY", "SELL"):
    auto_key = (
        f"{symbol}-{interval}-{analysis['signal']}-"
        f"{round(float(analysis['entry']), 2)}"
    )

    if auto_key != st.session_state.last_auto_signal:
        if np.isfinite(analysis["sl"]) and np.isfinite(analysis["tp"]):
            signal_id = f"auto-{symbol}-{uuid.uuid4().hex[:12]}"

            ok, result = send_remote_signal(
                bridge_url,
                bridge_token,
                remote_symbol,
                analysis["signal"],
                remote_volume,
                analysis["entry"],
                analysis["sl"],
                analysis["tp"],
                signal_id,
            )

            if ok:
                st.session_state.last_auto_signal = auto_key
                st.session_state.last_auto_result = result
                st.toast("تم إرسال إشارة MILA إلى MT5 🚀")
            else:
                st.session_state.last_auto_result = result


# ============================================================
# 12) HEADER
# ============================================================
st.markdown(
    f"""
<div class="hero">
    <h1>✨ MILA Volume Profile PRO</h1>
    <p>محطة تحليل الذهب والفضة — Volume Profile + Liquidity + Trend + Remote MT5</p>
</div>
""",
    unsafe_allow_html=True,
)

status_col1, status_col2, status_col3 = st.columns(3)

with status_col1:
    st.metric("السوق", "مفتوح 🟢" if market_open else "مغلق 🔴")

with status_col2:
    if not df.empty:
        last_price = float(df["close"].iloc[-1])
        st.metric(symbol, f"{last_price:.2f}")
    else:
        st.metric(symbol, "—")

with status_col3:
    st.metric("الاتجاه", analysis["trend"])


# ============================================================
# 13) SIGNAL CARD
# ============================================================
signal = analysis["signal"]

if signal == "BUY":
    st.markdown(
        f"""
<div class="signal-buy">
<h2>🟢 BUY — إشارة شراء</h2>
<p><b>Entry:</b> {analysis['entry']:.2f}
&nbsp;&nbsp; <b>SL:</b> {analysis['sl']:.2f}
&nbsp;&nbsp; <b>TP:</b> {analysis['tp']:.2f}</p>
<p><b>Score:</b> {analysis['score']} / 10+
&nbsp;&nbsp; <b>RSI:</b> {analysis['rsi']:.1f}</p>
<p>{analysis['reason']}</p>
</div>
""",
        unsafe_allow_html=True,
    )
elif signal == "SELL":
    st.markdown(
        f"""
<div class="signal-sell">
<h2>🔴 SELL — إشارة بيع</h2>
<p><b>Entry:</b> {analysis['entry']:.2f}
&nbsp;&nbsp; <b>SL:</b> {analysis['sl']:.2f}
&nbsp;&nbsp; <b>TP:</b> {analysis['tp']:.2f}</p>
<p><b>Score:</b> {analysis['score']} / 10+
&nbsp;&nbsp; <b>RSI:</b> {analysis['rsi']:.1f}</p>
<p>{analysis['reason']}</p>
</div>
""",
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f"""
<div class="signal-neutral">
<h2>🟡 WAIT — لا توجد صفقة مؤكدة</h2>
<p><b>Buy Score:</b> {analysis['buy_score']}
&nbsp;&nbsp; <b>Sell Score:</b> {analysis['sell_score']}</p>
<p>{analysis['reason']}</p>
</div>
""",
        unsafe_allow_html=True,
    )


# ============================================================
# 14) METRICS
# ============================================================
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.metric("RSI", f"{analysis['rsi']:.1f}" if np.isfinite(analysis["rsi"]) else "—")
with c2:
    st.metric("ATR", f"{analysis['atr']:.2f}" if np.isfinite(analysis["atr"]) else "—")
with c3:
    st.metric("POC", f"{analysis['poc']:.2f}" if np.isfinite(analysis["poc"]) else "—")
with c4:
    st.metric("VAH", f"{analysis['vah']:.2f}" if np.isfinite(analysis["vah"]) else "—")
with c5:
    st.metric("VAL", f"{analysis['val']:.2f}" if np.isfinite(analysis["val"]) else "—")


# ============================================================
# 15) PROFILE / DATA CHART
# ============================================================
if not df.empty:
    chart_df = df.tail(120)[["close", "ema21", "ema50", "ema200"]].copy()
    chart_df.columns = ["السعر", "EMA21", "EMA50", "EMA200"]
    st.line_chart(chart_df, height=350)

    profile = calc_volume_profile(
        df,
        rows=profile_rows,
        lookback=lookback,
        va_pct=va_pct,
    )

    if len(profile["bins"]) > 0:
        profile_df = pd.DataFrame(
            {
                "Price": profile["bins"],
                "Volume": profile["volumes"],
            }
        ).set_index("Price")
        st.markdown("### 📊 Volume Profile")
        st.bar_chart(profile_df, height=300)


# ============================================================
# 16) TRADINGVIEW
# ============================================================
st.markdown("### 📺 TradingView — XAUUSD")

tv_interval = {
    "1m": "1",
    "5m": "5",
    "15m": "15",
    "30m": "30",
    "1h": "60",
    "4h": "240",
}.get(interval, "5")

tradingview_widget_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
html, body {{
    margin: 0;
    padding: 0;
    width: 100%;
    height: 100%;
    overflow: hidden;
    background: #071018;
}}
.tradingview-widget-container {{
    width: 100%;
    height: 100%;
}}
</style>
</head>
<body>
<div class="tradingview-widget-container">
<div id="tradingview_chart" style="width:100%;height:100%;"></div>
<script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
<script type="text/javascript">
new TradingView.widget({{
    "autosize": true,
    "symbol": "OANDA:{symbol}",
    "interval": "{tv_interval}",
    "timezone": "Etc/UTC",
    "theme": "dark",
    "style": "1",
    "locale": "ar",
    "enable_publishing": false,
    "allow_symbol_change": true,
    "hide_side_toolbar": false,
    "withdateranges": true,
    "details": true,
    "hotlist": false,
    "calendar": false,
    "studies": [
        "Volume@tv-basicstudies",
        "RSI@tv-basicstudies"
    ],
    "container_id": "tradingview_chart"
}});
</script>
</div>
</body>
</html>
"""

components.html(
    tradingview_widget_html,
    height=620,
    scrolling=False,
)


# ============================================================
# 17) REMOTE MT5 MANUAL ORDER
# ============================================================
if remote_enabled:
    st.markdown("### 🌐 Remote MT5")

    if bridge_status:
        st.success("Bridge API متاح.")
        with st.expander("حالة Bridge"):
            st.json(bridge_status)

    st.caption(
        "الإرسال يتم إلى Bridge API على الـ VPS، وبعدها EA داخل MT5 هو الذي ينفذ الصفقة."
    )

    if signal in ("BUY", "SELL") and np.isfinite(analysis["sl"]) and np.isfinite(analysis["tp"]):
        st.markdown(
            f"**إشارة MILA الحالية:** `{signal}` — "
            f"Entry `{analysis['entry']:.2f}` — "
            f"SL `{analysis['sl']:.2f}` — "
            f"TP `{analysis['tp']:.2f}`"
        )

    m1, m2 = st.columns(2)

    with m1:
        manual_side = st.selectbox("نوع الأمر", ["BUY", "SELL"])

    with m2:
        manual_volume = st.number_input(
            "Lot للأمر اليدوي",
            min_value=0.01,
            max_value=100.0,
            value=float(remote_volume),
            step=0.01,
        )

    manual_entry = st.number_input(
        "Entry",
        min_value=0.0,
        value=float(analysis["entry"]) if np.isfinite(analysis["entry"]) else 0.0,
        step=0.01,
        format="%.2f",
    )

    if manual_side == "BUY":
        auto_sl = manual_entry - max(float(analysis["atr"]) * 0.5, 1.0) if np.isfinite(analysis["atr"]) else manual_entry - 2
        auto_tp = manual_entry + max(float(analysis["atr"]) * rr, 1.5) if np.isfinite(analysis["atr"]) else manual_entry + 3
    else:
        auto_sl = manual_entry + max(float(analysis["atr"]) * 0.5, 1.0) if np.isfinite(analysis["atr"]) else manual_entry + 2
        auto_tp = manual_entry - max(float(analysis["atr"]) * rr, 1.5) if np.isfinite(analysis["atr"]) else manual_entry - 3

    manual_sl = st.number_input(
        "SL",
        min_value=0.0,
        value=float(round(auto_sl, 2)),
        step=0.01,
        format="%.2f",
    )

    manual_tp = st.number_input(
        "TP",
        min_value=0.0,
        value=float(round(auto_tp, 2)),
        step=0.01,
        format="%.2f",
    )

    manual_confirm = st.checkbox(
        "أؤكد إرسال هذا الأمر إلى MT5",
        value=False,
    )

    if st.button(
        "🚀 إرسال الأمر إلى MT5",
        type="primary",
        use_container_width=True,
        disabled=not manual_confirm,
    ):
        signal_id = f"manual-{remote_symbol}-{uuid.uuid4().hex[:12]}"

        ok, result = send_remote_signal(
            bridge_url,
            bridge_token,
            remote_symbol,
            manual_side,
            manual_volume,
            manual_entry,
            manual_sl,
            manual_tp,
            signal_id,
        )

        if ok:
            st.success(f"تم إرسال الأمر بنجاح — ID: {signal_id}")
            st.json(result)
        else:
            st.error(result)


# ============================================================
# 18) AI ADVISOR
# ============================================================
st.markdown("### 🤖 المستشار الذكي")

if client is None:
    st.info("للتفعيل: أضف GROQ_API_KEY إلى Streamlit Secrets أو Environment.")
else:
    if st.button("✨ اطلب تحليل AI الحالي", use_container_width=True):
        context = f"""
السوق: {symbol}
الفريم: {interval}
السعر: {analysis['entry']:.2f}
الإشارة: {analysis['signal']}
الترند: {analysis['trend']}
RSI: {analysis['rsi']:.2f}
ATR: {analysis['atr']:.2f}
POC: {analysis['poc']:.2f}
VAH: {analysis['vah']:.2f}
VAL: {analysis['val']:.2f}
Buy Score: {analysis['buy_score']}
Sell Score: {analysis['sell_score']}
الأسباب: {analysis['reason']}

حلل المعطيات باختصار، واذكر الاتجاه، مناطق الدخول، المخاطر،
ولا تعتبر التحليل ضماناً للربح.
"""
        try:
            response = client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[
                    {
                        "role": "system",
                        "content": "أنت محلل فني محترف للذهب والفضة. قدم تحليلاً واضحاً وغير مبالغ فيه.",
                    },
                    {"role": "user", "content": context},
                ],
                temperature=0.2,
            )
            st.info(response.choices[0].message.content)
        except Exception as exc:
            st.error(f"تعذر الحصول على تحليل AI: {exc}")


# ============================================================
# 19) CHAT
# ============================================================
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "مرحباً! أنا مستشار MILA. اسألني عن XAUUSD أو XAGUSD أو الإشارة الحالية."
        }
    ]

with st.expander("💬 محادثة المستشار"):
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_input = st.chat_input("اكتب سؤالك...")
    if user_input:
        st.session_state.messages.append(
            {"role": "user", "content": user_input}
        )

        if client is None:
            reply = "⚠️ لم يتم إعداد GROQ_API_KEY."
        else:
            try:
                payload = [
                    {
                        "role": "system",
                        "content": (
                            f"أنت مستشار تداول للذهب والفضة. "
                            f"السوق الحالي {symbol} والفريم {interval}. "
                            f"إشارة MILA الحالية: {analysis['signal']}. "
                            f"لا تقدم ضمانات ربح."
                        ),
                    }
                ]
                payload.extend(st.session_state.messages)

                response = client.chat.completions.create(
                    model="openai/gpt-oss-20b",
                    messages=payload,
                    temperature=0.3,
                )
                reply = response.choices[0].message.content
            except Exception as exc:
                reply = f"تعذر الرد حالياً: {exc}"

        st.session_state.messages.append(
            {"role": "assistant", "content": reply}
        )
        st.rerun()


# ============================================================
# 20) FOOTER
# ============================================================
st.markdown("---")
st.caption(
    "MILA PRO • التحليل تعليمي وليس ضماناً للربح • ابدأ دائماً بحساب Demo قبل التفعيل الحقيقي."
)
