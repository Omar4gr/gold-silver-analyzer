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
    initial_sidebar_state="expanded"
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
st.caption("تحليل فني وتوصيات ذكية لحظية مع إشعارات التليجرام")

# ---------------------------------------------------------
# 2. إعدادات الإشعارات (الشريط الجانبي)
# ---------------------------------------------------------
with st.sidebar:
    st.header("🔔 إعدادات الإشعارات (Telegram)")
    enable_notifications = st.checkbox("تفعيل الإشعارات الفورية", value=False)
    telegram_bot_token = st.text_input("Bot Token", type="password", placeholder="123456789:ABCDefgh...")
    telegram_chat_id = st.text_input("Chat ID", type="password", placeholder="987654321")

# دالة إرسال إشعار عبر التليجرام
def send_telegram_notification(message):
    if enable_notifications and telegram_bot_token and telegram_chat_id:
        url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": telegram_chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        try:
            requests.post(url, data=payload, timeout=5)
        except Exception as e:
            st.sidebar.error(f"فشل إرسال الإشعار: {e}")

# ---------------------------------------------------------
# 3. دالة جلب البيانات الفورية والتحليل الفني
# ---------------------------------------------------------
@st.cache_data(ttl=15)
def get_market_data(symbol_type):
    symbol = "XAUUSD=X" if symbol_type == "gold" else "XAGUSD=X"
    fallback_symbol = "GC=F" if symbol_type == "gold" else "SI=F"
    
    df = pd.DataFrame()
    last_error = ""

    try:
        data = yf.Ticker(symbol).history(period="5d", interval="5m")
        if not data.empty and len(data) > 5:
            df = data
        else:
            data_daily = yf.Ticker(symbol).history(period="1mo", interval="1d")
            if not data_daily.empty:
                df = data_daily
    except Exception as e:
        last_error = str(e)

    if df.empty:
        try:
            data = yf.Ticker(fallback_symbol).history(period="5d", interval="5m")
            if not data.empty:
                df = data
        except Exception as e:
            last_error = str(e)

    if df.empty:
        return None, None, f"فشل جلب البيانات. ({last_error})"

    try:
        df = df.dropna(subset=['Close'])
        close = df['Close']

        window_sma = min(20, len(df))
        window_ema = min(50, len(df))

        df['SMA_20'] = SMAIndicator(close=close, window=window_sma).sma_indicator()
        df['EMA_50'] = EMAIndicator(close=close, window=window_ema).ema_indicator()
        df['RSI'] = RSIIndicator(close=close, window=14).rsi()
        
        macd_obj = MACD(close=close)
        df['MACD'] = macd_obj.macd()

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
# 4. واجهة العرض مع نظام تتبع التوصيات
# ---------------------------------------------------------
if 'last_signal' not in st.session_state:
    st.session_state.last_signal = {'gold': None, 'silver': None}

tab_gold, tab_silver = st.tabs(["🥇 الذهب (XAUUSD)", "🥈 الفضة (XAGUSD)"])

def render_market_view(symbol_type, name):
    df, analysis, error = get_market_data(symbol_type)
    
    if error or df is None:
        st.error(f"تعذر جلب بيانات {name}: {error}")
        return

    st.metric(label=f"سعر {name} الحالي (Spot)", value=f"${analysis['price']:.2f}", delta=f"{analysis['change']:+.2f}")

    rec_text = f"**توصية الذكاء الاصطناعي:** {analysis['recommendation']}\n\n_{analysis['desc']}_"
    if analysis['color'] == "green":
        st.success(rec_text)
    elif analysis['color'] == "red":
        st.error(rec_text)
    else:
        st.warning(rec_text)

    # فحص التوصية وإرسال الإشعار عند تغير الإشارة فقط
    current_rec = analysis['recommendation']
    if current_rec in ["شراء (Buy)", "بيع (Sell)"]:
        if st.session_state.last_signal[symbol_type] != current_rec:
            st.session_state.last_signal[symbol_type] = current_rec
            
            msg = f"🚨 *تنبيه جديد - {name}*\n\n" \
                  f"📊 *التوصية:* {current_rec}\n" \
                  f"💵 *السعر الحالي:* ${analysis['price']:.2f}\n" \
                  f"📉 *مؤشر RSI:* {analysis['rsi']:.1f}\n\n" \
                  f"📝 {analysis['desc']}"
            
            send_telegram_notification(msg)

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
