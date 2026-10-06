import datetime
import os
import time
from typing import Optional

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


# =========================================================
# 1) إعدادات الصفحة
# =========================================================
st.set_page_config(
    page_title="MILA Gold AI • Volume Profile PRO",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
:root { --bg:#080b10; --panel:#0d1117; --panel2:#111720; --line:#26303c; }
.stApp { background: radial-gradient(circle at 15% 0%, #14202c 0%, #080b10 38%, #07090d 100%); }
.block-container { max-width: 1500px; padding-top: 1rem; padding-bottom: 2rem; }
[data-testid="stSidebar"] { background: #090d12; border-right: 1px solid #202936; }
.mila-card {
    background: linear-gradient(145deg, rgba(18,24,32,.96), rgba(9,13,18,.96));
    border: 1px solid #26303c; border-radius: 16px; padding: 16px;
    box-shadow: 0 10px 35px rgba(0,0,0,.24); margin-bottom: 12px;
}
.mila-title { font-size: 28px; font-weight: 800; letter-spacing: .4px; }
.mila-muted { color:#9aa6b2; font-size:13px; }
.mila-buy { color:#55f39a; font-weight:800; }
.mila-sell { color:#ff6670; font-weight:800; }
.mila-wait { color:#ffc857; font-weight:800; }
.metric-box {
    background:#0d1117; border:1px solid #202936; border-radius:12px;
    padding:12px 14px; min-height:78px;
}
.metric-label { color:#8d99a8; font-size:12px; }
.metric-value { color:#f3f6f8; font-size:20px; font-weight:800; margin-top:4px; }
</style>
""", unsafe_allow_html=True)


# =========================================================
# 2) Groq / OpenAI-compatible client
# =========================================================
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", os.getenv("GROQ_API_KEY", ""))
client = None
if GROQ_API_KEY and OpenAI is not None:
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=GROQ_API_KEY,
    )


# =========================================================
# 3) حالة السوق
# =========================================================
def check_market_status():
    iraq_now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3)
    weekday = iraq_now.weekday()
    hour = iraq_now.hour

    if weekday == 5:
        return {
            "is_open": False,
            "status_text": "السوق مغلق • عطلة نهاية الأسبوع 🔴",
            "reopen_time": "يفتح السوق عادةً مع بداية جلسة الإثنين",
        }

    if weekday == 6 and hour < 1:
        return {
            "is_open": False,
            "status_text": "السوق مغلق • عطلة نهاية الأسبوع 🔴",
            "reopen_time": "بانتظار افتتاح الأسبوع",
        }

    if weekday == 6:
        return {
            "is_open": False,
            "status_text": "السوق مغلق • بانتظار افتتاح الأسبوع 🔴",
            "reopen_time": "بانتظار افتتاح سوق الفوركس",
        }

    return {
        "is_open": True,
        "status_text": "السوق مفتوح 🟢",
        "reopen_time": "",
    }


market_status = check_market_status()


# =========================================================
# 4) جلب بيانات حقيقية — Yahoo Finance
# =========================================================
@st.cache_data(ttl=30, show_spinner=False)
def fetch_market_data(period="5d", interval="5m"):
    if yf is None:
        return pd.DataFrame(), "مكتبة yfinance غير مثبتة."

    try:
        df = yf.download(
            "XAUUSD=X",
            period=period,
            interval=interval,
            auto_adjust=False,
            progress=False,
            threads=False,
        )

        if df is None or df.empty:
            return pd.DataFrame(), "تعذر الحصول على بيانات XAUUSD حالياً."

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        needed = ["Open", "High", "Low", "Close", "Volume"]
        for col in needed:
            if col not in df.columns:
                if col == "Volume":
                    df[col] = 0.0
                else:
                    return pd.DataFrame(), f"البيانات ناقصة: {col}"

        df = df[needed].copy()
        df = df.dropna(subset=["Open", "High", "Low", "Close"])
        return df, ""
    except Exception as e:
        return pd.DataFrame(), f"خطأ في جلب البيانات: {e}"


# =========================================================
# 5) مؤشرات مساعدة
# =========================================================
def rsi(series, length=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    avg_loss = loss.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def atr(df, length=14):
    prev_close = df["Close"].shift(1)
    tr = pd.concat(
        [
            df["High"] - df["Low"],
            (df["High"] - prev_close).abs(),
            (df["Low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()


def ema(series, length):
    return series.ewm(span=length, adjust=False).mean()


# =========================================================
# 6) Volume Profile PRO — تحويل منطق Pine إلى Python
# =========================================================
def calc_profile(df, lb=120, rows=30, va_pct=0.70):
    if len(df) < max(lb, 20):
        return None

    x = df.iloc[-lb:].copy()
    hi = float(x["High"].max())
    lo = float(x["Low"].min())

    if hi <= lo:
        return None

    step = (hi - lo) / rows
    vols = [0.0] * rows
    buy_vols = [0.0] * rows

    for _, row in x.iterrows():
        s = max(0, min(rows - 1, int((float(row["Low"]) - lo) / step)))
        e = max(0, min(rows - 1, int((float(row["High"]) - lo) / step)))
        v = float(row["Volume"]) if pd.notna(row["Volume"]) else 0.0
        if v <= 0:
            # Yahoo قد يعيد Volume=0 للذهب؛ نعطي كل شمعة وزناً واحداً
            v = 1.0

        share = v / (e - s + 1)
        up = float(row["Close"]) >= float(row["Open"])

        for r in range(s, e + 1):
            vols[r] += share
            if up:
                buy_vols[r] += share

    poc_idx = max(range(rows), key=lambda i: vols[i])
    total = sum(vols)
    acc = vols[poc_idx]
    up = poc_idx
    dn = poc_idx

    while acc < total * va_pct and (up < rows - 1 or dn > 0):
        vu = vols[up + 1] if up < rows - 1 else -1
        vd = vols[dn - 1] if dn > 0 else -1

        if vu >= vd:
            up += 1
            acc += vu
        else:
            dn -= 1
            acc += vd

    poc = lo + step * (poc_idx + 0.5)
    vah = lo + step * (up + 1)
    val = lo + step * dn

    return {
        "hi": hi,
        "lo": lo,
        "step": step,
        "vols": vols,
        "buy_vols": buy_vols,
        "poc": poc,
        "vah": vah,
        "val": val,
        "rows": rows,
    }


def analyze_mila(
    df,
    lb=120,
    rows=30,
    va_pct=0.70,
    sweep_len=20,
    zone_atr=0.30,
    vol_mult=1.20,
    atr_mult=0.50,
    rr=1.50,
):
    if len(df) < max(lb + 5, 60):
        return None

    d = df.copy()
    d["EMA21"] = ema(d["Close"], 21)
    d["EMA50"] = ema(d["Close"], 50)
    d["EMA200"] = ema(d["Close"], 200)
    d["RSI"] = rsi(d["Close"], 14)
    d["ATR"] = atr(d, 14)
    d["VolAvg"] = d["Volume"].rolling(20).mean()

    profile = calc_profile(d, lb, rows, va_pct)
    if profile is None:
        return None

    row = d.iloc[-1]
    prev = d.iloc[-2]
    price = float(row["Close"])
    atr_now = float(row["ATR"]) if pd.notna(row["ATR"]) else (profile["hi"] - profile["lo"]) / rows

    trend_up = price > row["EMA50"] and row["EMA50"] > row["EMA200"]
    trend_dn = price < row["EMA50"] and row["EMA50"] < row["EMA200"]

    short_up = row["EMA21"] > row["EMA50"] and row["EMA21"] > d["EMA21"].iloc[-4]
    short_dn = row["EMA21"] < row["EMA50"] and row["EMA21"] < d["EMA21"].iloc[-4]

    rsi_now = float(row["RSI"])
    rsi_prev = float(d["RSI"].iloc[-2])

    body = abs(price - float(row["Open"]))
    rng = float(row["High"] - row["Low"])
    low_wick = min(float(row["Open"]), price) - float(row["Low"])
    up_wick = float(row["High"]) - max(float(row["Open"]), price)

    bull_engulf = (
        price > float(row["Open"])
        and float(prev["Close"]) < float(prev["Open"])
        and price >= float(prev["Open"])
        and float(row["Open"]) <= float(prev["Close"])
    )
    bear_engulf = (
        price < float(row["Open"])
        and float(prev["Close"]) > float(prev["Open"])
        and price <= float(prev["Open"])
        and float(row["Open"]) >= float(prev["Close"])
    )
    hammer = rng > 0 and low_wick >= body * 2 and (price - float(row["Low"])) / rng > 0.6
    shooting = rng > 0 and up_wick >= body * 2 and (float(row["High"]) - price) / rng > 0.6
    bull_break = price > float(row["Open"]) and price > float(prev["High"]) and body > rng * 0.5
    bear_break = price < float(row["Open"]) and price < float(prev["Low"]) and body > rng * 0.5
    bull_candle = bull_engulf or hammer or bull_break
    bear_candle = bear_engulf or shooting or bear_break

    recent_low = float(d["Low"].iloc[-sweep_len-1:-1].min())
    recent_high = float(d["High"].iloc[-sweep_len-1:-1].max())

    sweep_low = float(row["Low"]) < recent_low and price > recent_low and low_wick > body
    sweep_high = float(row["High"]) > recent_high and price < recent_high and up_wick > body

    near_val = (
        float(row["Low"]) <= profile["val"] + atr_now * zone_atr
        and price >= profile["val"] - atr_now * zone_atr
        and price < profile["poc"]
    )
    near_vah = (
        float(row["High"]) >= profile["vah"] - atr_now * zone_atr
        and price <= profile["vah"] + atr_now * zone_atr
        and price > profile["poc"]
    )

    vol_avg = float(row["VolAvg"]) if pd.notna(row["VolAvg"]) else 0.0
    volume_ok = float(row["Volume"]) > vol_avg * vol_mult if vol_avg > 0 else True

    brk_up = price > profile["vah"] and float(prev["Close"]) <= profile["vah"] and volume_ok
    brk_dn = price < profile["val"] and float(prev["Close"]) >= profile["val"] and volume_ok

    poc_buy = trend_up and float(row["Low"]) <= profile["poc"] + atr_now * zone_atr and price > profile["poc"]
    poc_sell = trend_dn and float(row["High"]) >= profile["poc"] - atr_now * zone_atr and price < profile["poc"]

    corr_down = float(row["High"]) < float(prev["High"]) and float(prev["High"]) < float(d["High"].iloc[-3])
    corr_up = float(row["Low"]) > float(prev["Low"]) and float(prev["Low"]) > float(d["Low"].iloc[-3])

    pb_buy = short_up and price > row["EMA50"] and (
        corr_down or (float(row["Low"]) <= row["EMA21"] + atr_now * zone_atr and price >= row["EMA21"] - atr_now)
    )
    pb_sell = short_dn and price < row["EMA50"] and (
        corr_up or (float(row["High"]) >= row["EMA21"] - atr_now * zone_atr and price <= row["EMA21"] + atr_now)
    )

    # ترتيب الأولويات مطابق لترتيب الإشارة في Pine.
    buy_candidates = []
    if poc_buy:
        buy_candidates.append((5, profile["poc"], "ارتداد من POC"))
    if pb_buy:
        buy_candidates.append((6, float(row["EMA50"]), "تصحيح في ترند صاعد"))
    if near_val:
        buy_candidates.append((1, profile["val"], "ارتداد من VAL"))
    if sweep_low:
        buy_candidates.append((3, recent_low, "سحب سيولة"))
    if brk_up:
        buy_candidates.append((2, profile["vah"], "اختراق VAH"))

    sell_candidates = []
    if poc_sell:
        sell_candidates.append((5, profile["poc"], "ارتداد من POC"))
    if pb_sell:
        sell_candidates.append((6, float(row["EMA50"]), "تصحيح في ترند هابط"))
    if near_vah:
        sell_candidates.append((1, profile["vah"], "ارتداد من VAH"))
    if sweep_high:
        sell_candidates.append((3, recent_high, "سحب سيولة"))
    if brk_dn:
        sell_candidates.append((2, profile["val"], "اختراق VAL"))

    buy_type, buy_lvl, buy_name = buy_candidates[-1] if buy_candidates else (0, None, "")
    sell_type, sell_lvl, sell_name = sell_candidates[-1] if sell_candidates else (0, None, "")

    buy_rsi_ok = rsi_now > rsi_prev and (
        (buy_type == 2 and rsi_now > 50)
        or (buy_type == 1 and rsi_now < 65)
        or (buy_type == 6 and rsi_now > 40)
        or buy_type not in (1, 2, 6)
    )
    sell_rsi_ok = rsi_now < rsi_prev and (
        (sell_type == 2 and rsi_now < 50)
        or (sell_type == 1 and rsi_now > 35)
        or (sell_type == 6 and rsi_now < 60)
        or sell_type not in (1, 2, 6)
    )

    buy_trend_ok = (
        (buy_type in (2, 5) and price > row["EMA50"])
        or (buy_type == 6 and short_up and price > row["EMA50"])
        or (buy_type == 1 and (not trend_dn or bull_engulf))
        or buy_type not in (1, 2, 5, 6)
    )
    sell_trend_ok = (
        (sell_type in (2, 5) and price < row["EMA50"])
        or (sell_type == 6 and short_dn and price < row["EMA50"])
        or (sell_type == 1 and (not trend_up or bear_engulf))
        or sell_type not in (1, 2, 5, 6)
    )

    buy_signal = buy_type != 0 and bull_candle and buy_rsi_ok and buy_trend_ok
    sell_signal = sell_type != 0 and bear_candle and sell_rsi_ok and sell_trend_ok

    direction = "BUY" if buy_signal else "SELL" if sell_signal else "WAIT"

    if direction == "BUY":
        sl = float(row["Low"]) - atr_now * atr_mult
        risk = max(price - sl, atr_now * 0.1)
        if buy_type in (1, 3, 4) and profile["poc"] > price + risk * 0.8:
            tp = profile["poc"]
        elif buy_type == 6 and recent_high > price + risk:
            tp = recent_high
        else:
            tp = price + risk * rr
    elif direction == "SELL":
        sl = float(row["High"]) + atr_now * atr_mult
        risk = max(sl - price, atr_now * 0.1)
        if sell_type in (1, 3, 4) and profile["poc"] < price - risk * 0.8:
            tp = profile["poc"]
        elif sell_type == 6 and recent_low < price - risk:
            tp = recent_low
        else:
            tp = price - risk * rr
    else:
        sl = None
        tp = None

    score = 0
    if direction != "WAIT":
        score += int((price > row["EMA50"]) if direction == "BUY" else (price < row["EMA50"]))
        score += int(rsi_now > rsi_prev if direction == "BUY" else rsi_now < rsi_prev)
        score += int(float(row["Volume"]) > vol_avg if vol_avg > 0 else 1)
        score += int(bull_candle if direction == "BUY" else bear_candle)

    trend_text = "صاعد 📈" if trend_up else "هابط 📉" if trend_dn else "عرضي ↔️"
    short_text = "صاعد 📈" if short_up else "هابط 📉" if short_dn else "عرضي ↔️"

    position = (
        "فوق منطقة القيمة" if price > profile["vah"]
        else "تحت منطقة القيمة" if price < profile["val"]
        else "داخل منطقة القيمة"
    )

    return {
        "price": price,
        "change": (price / float(prev["Close"]) - 1) * 100,
        "rsi": rsi_now,
        "atr": atr_now,
        "poc": profile["poc"],
        "vah": profile["vah"],
        "val": profile["val"],
        "trend": trend_text,
        "short_trend": short_text,
        "position": position,
        "direction": direction,
        "signal_name": buy_name if direction == "BUY" else sell_name if direction == "SELL" else "—",
        "entry": price if direction != "WAIT" else None,
        "tp": tp,
        "sl": sl,
        "score": score,
        "bull_candle": bull_candle,
        "bear_candle": bear_candle,
        "profile": profile,
        "recent_low": recent_low,
        "recent_high": recent_high,
        "df": d,
    }


# =========================================================
# 7) جلب وتحليل
# =========================================================
with st.sidebar:
    st.subheader("⚙️ إعدادات MILA")

    timeframe = st.selectbox(
        "الفريم",
        ["5m", "15m", "30m", "1h"],
        index=0,
    )

    lb = st.slider("عدد الشموع للبروفايل", 50, 300, 120, 10)
    rows = st.slider("عدد الصفوف", 10, 60, 30, 5)
    va_pct = st.slider("منطقة القيمة %", 50, 95, 70) / 100
    vol_mult = st.slider("مضاعف الفوليوم", 0.8, 2.5, 1.2, 0.1)
    rr = st.slider("الهدف R:R", 0.5, 4.0, 1.5, 0.1)

    st.markdown("---")
    st.subheader("🤖 حالة السوق")

    if market_status["is_open"]:
        st.success(market_status["status_text"])
    else:
        st.warning(market_status["status_text"])

    if st.button("🔄 تحديث البيانات والتحليل", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


df, data_error = fetch_market_data(
    period="5d" if timeframe != "1h" else "1mo",
    interval=timeframe,
)

analysis = analyze_mila(
    df,
    lb=lb,
    rows=rows,
    va_pct=va_pct,
    vol_mult=vol_mult,
    rr=rr,
)


# =========================================================
# 8) الرأس
# =========================================================
st.markdown(
    '<div class="mila-card">'
    '<div class="mila-title">📈 MILA GOLD AI • Volume Profile PRO</div>'
    '<div class="mila-muted">تحليل XAUUSD • POC / VAH / VAL • إشارات دخول • TP / SL</div>'
    '</div>',
    unsafe_allow_html=True,
)

if data_error:
    st.error(data_error)
    st.info("ثبّت المتطلبات: `pip install yfinance pandas openai streamlit`")
elif analysis is None:
    st.warning("البيانات الحالية غير كافية لحساب Volume Profile. جرّب فريم آخر أو انتظر تحميل بيانات أكثر.")
else:
    # =====================================================
    # 9) لوحة الإشارة
    # =====================================================
    direction = analysis["direction"]
    if direction == "BUY":
        signal_text = "شراء الآن 🟢"
        signal_class = "mila-buy"
    elif direction == "SELL":
        signal_text = "بيع الآن 🔴"
        signal_class = "mila-sell"
    else:
        signal_text = "انتظار ⏳"
        signal_class = "mila-wait"

    stars = "★" * analysis["score"] + "☆" * (4 - analysis["score"])

    cols = st.columns(7)
    cards = [
        ("الحالة", signal_text, signal_class),
        ("السعر", f'{analysis["price"]:.2f}', ""),
        ("POC", f'{analysis["poc"]:.2f}', ""),
        ("VAH", f'{analysis["vah"]:.2f}', ""),
        ("VAL", f'{analysis["val"]:.2f}', ""),
        ("RSI", f'{analysis["rsi"]:.1f}', ""),
        ("القوة", stars, "mila-buy" if analysis["score"] >= 3 else "mila-wait"),
    ]

    for col, (label, value, cls) in zip(cols, cards):
        with col:
            st.markdown(
                f'<div class="metric-box"><div class="metric-label">{label}</div>'
                f'<div class="metric-value {cls}">{value}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("")

    # =====================================================
    # 10) تفاصيل الصفقة
    # =====================================================
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("الترند العام", analysis["trend"])
    c2.metric("الترند القصير", analysis["short_trend"])
    c3.metric("موقع السعر", analysis["position"])
    c4.metric("نوع الفرصة", analysis["signal_name"])
    c5.metric("التغير", f'{analysis["change"]:+.2f}%')

    if direction != "WAIT":
        p1, p2, p3 = st.columns(3)
        p1.metric("سعر الدخول", f'{analysis["entry"]:.2f}')
        p2.metric("TP", f'{analysis["tp"]:.2f}')
        p3.metric("SL", f'{analysis["sl"]:.2f}')

    # =====================================================
    # 11) Volume Profile مرئي داخل التطبيق
    # =====================================================
    st.markdown("### 📊 Volume Profile PRO")

    prof = analysis["profile"]
    profile_df = pd.DataFrame({
        "السعر": [
            prof["lo"] + prof["step"] * (i + 0.5)
            for i in range(prof["rows"])
        ],
        "الحجم": prof["vols"],
        "شراء": prof["buy_vols"],
    })
    profile_df["بيع"] = profile_df["الحجم"] - profile_df["شراء"]

    max_vol = max(profile_df["الحجم"].max(), 1)
    profile_df["نسبي"] = profile_df["الحجم"] / max_vol

    left, right = st.columns([2.2, 1])

    with left:
        st.bar_chart(
            profile_df.set_index("السعر")[["شراء", "بيع"]],
            height=440,
        )

    with right:
        st.markdown(
            f"""
            <div class="mila-card">
            <h3>🎯 مستويات البروفايل</h3>
            <p><b>POC:</b> {analysis["poc"]:.2f}</p>
            <p><b>VAH:</b> {analysis["vah"]:.2f}</p>
            <p><b>VAL:</b> {analysis["val"]:.2f}</p>
            <hr>
            <p><b>الفرصة:</b> {analysis["signal_name"]}</p>
            <p><b>القوة:</b> {stars}</p>
            <p><b>RSI:</b> {analysis["rsi"]:.1f}</p>
            <p><b>ATR:</b> {analysis["atr"]:.2f}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # =====================================================
    # 12) TradingView
    # =====================================================
    st.markdown("### 🖥️ الشارت")

    tv_interval = timeframe
    tradingview_widget_html = f"""
    <div class="tradingview-widget-container" style="height:620px;width:100%;border-radius:14px;overflow:hidden;">
      <div id="tradingview_chart" style="height:100%;width:100%"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "width":"100%",
        "height":620,
        "symbol":"OANDA:XAUUSD",
        "interval":"{tv_interval}",
        "timezone":"Etc/UTC",
        "theme":"dark",
        "style":"1",
        "locale":"ar",
        "enable_publishing":false,
        "hide_side_toolbar":false,
        "allow_symbol_change":true,
        "details":true,
        "hotlist":true,
        "calendar":false,
        "container_id":"tradingview_chart"
      }});
      </script>
    </div>
    """
    components.html(tradingview_widget_html, height=640)

    # =====================================================
    # 13) AI Advisor
    # =====================================================
    st.markdown("### 🤖 المستشار الذكي")

    if client is not None:
        if st.button("🧠 تحليل الإشارة بالذكاء الاصطناعي"):
            prompt = f"""
أنت محلل فني محترف. حلل XAUUSD اعتماداً على هذه البيانات:
السعر: {analysis['price']:.2f}
POC: {analysis['poc']:.2f}
VAH: {analysis['vah']:.2f}
VAL: {analysis['val']:.2f}
RSI: {analysis['rsi']:.1f}
الترند العام: {analysis['trend']}
الترند القصير: {analysis['short_trend']}
موقع السعر: {analysis['position']}
نوع الفرصة: {analysis['signal_name']}
الإشارة: {signal_text}
الدخول: {analysis['entry']}
TP: {analysis['tp']}
SL: {analysis['sl']}

أعطني تحليلاً قصيراً جداً بالعربية، واذكر سبب الإشارة ومستوى الإبطال، بدون ادعاء ضمان الربح.
"""
            try:
                response = client.chat.completions.create(
                    model="openai/gpt-oss-20b",
                    messages=[
                        {
                            "role": "system",
                            "content": "أنت مستشار تحليل فني. لا تقدم ضمانات للربح.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                )
                st.info(response.choices[0].message.content)
            except Exception as e:
                st.error(f"تعذر تشغيل المستشار: {e}")
    else:
        st.caption("للتفعيل، ضع GROQ_API_KEY داخل Streamlit Secrets أو متغيرات البيئة.")

    # =====================================================
    # 14) محادثة المستشار
    # =====================================================
    st.markdown("### 💬 محادثة المستشار")

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "مرحباً 👋 اسألني عن XAUUSD أو POC/VAH/VAL أو الإشارة الحالية.",
            }
        ]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_input = st.chat_input("اسأل عن السوق أو الإشارة الحالية...")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            if client is None:
                reply = "المستشار غير مفعّل. أضف GROQ_API_KEY إلى Secrets."
            else:
                context = f"""
السعر {analysis['price']:.2f}، POC {analysis['poc']:.2f}، VAH {analysis['vah']:.2f}،
VAL {analysis['val']:.2f}، RSI {analysis['rsi']:.1f}، الترند {analysis['trend']},
الإشارة {signal_text}، نوعها {analysis['signal_name']}.
"""
                payload = [
                    {
                        "role": "system",
                        "content": "أنت مستشار فني للذهب. أجب بالعربية بوضوح واختصار، ولا تضمن الربح.",
                    }
                ]
                payload.extend(st.session_state.messages[-8:])
                payload[-1]["content"] += "\n\nبيانات السوق الحالية:\n" + context

                try:
                    response = client.chat.completions.create(
                        model="openai/gpt-oss-20b",
                        messages=payload,
                        temperature=0.3,
                    )
                    reply = response.choices[0].message.content
                except Exception as e:
                    reply = f"تعذر الحصول على الرد حالياً: {e}"

            st.markdown(reply)
            st.session_state.messages.append(
                {"role": "assistant", "content": reply}
            )

st.caption("MILA • Volume Profile PRO — الإشارات تحليلية وليست ضماناً للربح.")
