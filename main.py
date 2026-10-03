import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator
from streamlit_autorefresh import st_autorefresh

# ---------------------------------------------------------
# 1. إعدادات الصفحة والتصميم
# ---------------------------------------------------------
st.set_page_config(
    page_title="محلل الأسواق الذكي",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# تحديث تلقائي كل 30 ثانية
st_autorefresh(interval=30000, key="datarefresh")

st.markdown("""
    <style>
    h1 { font-size: 1.8rem !important; text-align: center; }
    h2 { font-size: 1.3rem !important; }
    .block-container { padding-top: 1.5rem !important; padding-bottom: 1rem !important; }
    .stAlert { font-size: 0.95rem !important; border-radius: 10px; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("📈 محلل الأسواق الذكي")
st.caption("تحليل فني وتوصيات ذكية لحظية للذهب والفضة")

# ---------------------------------------------------------
# 2. دالة جلب البيانات الذكية المتعددة المصادر (تتجاوز الحظر)
# ---------------------------------------------------------
@st.cache_data(ttl=15)
def get_market_data(symbol_type):
    # رموز الذهب والفضة
    tickers = ["GC=F", "XAUUSD=X"] if symbol_type == "gold" else ["SI=F", "XAGUSD=X"]
    
    df = pd.DataFrame()
    last_error = ""

    # تجربة المصادر حتى ينجح أحدها
    for ticker in tickers:
        try:
            # محاولة جلب البيانات بفاصل 5 دقائق
            data = yf.Ticker(ticker).history(period="5d", interval="5m")
            if not data.empty and len(data) > 5:
                df = data
                break
            
            # إذا فشلت الـ 5 دقائق، جلب اليومية
            data_daily = yf.Ticker(ticker).history(period="1mo", interval="1d")
            if not data_daily.empty:
                df = data_daily
                break
        except Exception as e:
            last_error = str(e)
            continue

    if df.empty:
        return None, None, f"فشل جلب البيانات. يرجى المحاولة لاحقاً ({last_error})"

    try:
        # تنظيف البيانات
        df = df.dropna(subset=['Close'])
        close = df['Close']

        # حساب المؤشرات
        window_sma = min(20, len(df))
        window_ema = min(50, len(df))

        df['SMA_20'] = SMAIndicator(close=close, window=window_sma).sma_indicator()
        df['EMA_50'] = EMAIndicator(close=close, window=window_ema).ema_indicator()
        df['RSI'] = RSIIndicator(close=close, window=14).rsi_indicator()
        
        macd_obj = MACD(close=close)
        df['MACD'] = macd_obj.macd()
        df['MACD_Signal'] = macd_obj.macd_signal()

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        current_price = float(latest['Close'])
        price_change = float(current_price - prev['Close'])

        # خوارزمية التوصية
        score = 0
        if current_price > latest.get('SMA_20', current_price) and current_price > latest.get('EMA_50', current_price):
            score += 2
        elif current_price < latest.get('SMA_20', current_price) and current_price < latest.get('EMA_50', current_price):
            score -= 2

        rsi_val = latest.get('RSI', 50)
        if rsi_val < 30:
            score += 3
        elif rsi_val > 70:
            score -= 3

        if score >= 3:
            rec, color, desc = "شراء (Buy)", "green", "الاتجاه صاعد مع إشارات إيجابية قوية."
        elif score <= -3:
            rec, color, desc = "بيع (Sell)", "red", "الاتجاه هابط مع ضغط بيعي."
        else:
            rec, color, desc = "محايد (Hold)", "orange", "السوق في حالة تذبذب أو مغلق حالياً."

        analysis = {
            'price': current_price,
            'change': price_change,
            'rsi': rsi_val,
            'recommendation': rec,
            'color': color,
            'desc': desc
        }

        return df, analysis, None
    except Exception as e:
        return None, None, str(e)

# ---------------------------------------------------------
# 3. واجهة العرض
# ---------------------------------------------------------
tab_gold, tab_silver = st.tabs(["🥇 الذهب (XAU)", "🥈 الفضة (XAG)"])

def render_market_view(symbol_type, name):
    df, analysis, error = get_market_data(symbol_type)
    
    if error or df is None:
        st.error(f"تعذر جلب بيانات {name}: {error}")
        return

    st.metric(label=f"سعر {name} الحالي", value=f"${analysis['price']:.2f}", delta=f"{analysis['change']:+.2f}")

    rec_text = f"**توصية الذكاء الاصطناعي:** {analysis['recommendation']}\n\n_{analysis['desc']}_"
    if analysis['color'] == "green":
        st.success(rec_text)
    elif analysis['color'] == "red":
        st.error(rec_text)
    else:
        st.warning(rec_text)

    # الرسم البياني
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="السعر"
    ))
    if 'SMA_20' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='orange', width=1), name="SMA 20"))
    if 'EMA_50' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_50'], line=dict(color='lightblue', width=1), name="EMA 50"))

    fig.update_layout(
        margin=dict(l=5, r=5, t=5, b=5),
        height=320,
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

with tab_gold:
    render_market_view("gold", "الذهب")

with tab_silver:
    render_market_view("silver", "الفضة")

if st.button("🔄 تحديث البيانات"):
    st.cache_data.clear()
    st.rerun()
