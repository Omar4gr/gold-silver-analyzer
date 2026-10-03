import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator
from streamlit_autorefresh import st_autorefresh

# 1. إعدادات الصفحة والتصميم
st.set_page_config(
    page_title="محلل الأسواق الذكي",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# تحديث تلقائي كل 30 ثانية
st_autorefresh(interval=30000, key="datarefresh")

# تنسيق الخطوط والأحجام للشاشات الصغيرة
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

# 2. دالة جلب البيانات والتحليل
@st.cache_data(ttl=15)
def get_market_data(ticker_symbol):
    try:
        df = yf.download(ticker_symbol, period="5d", interval="5m", progress=False)
        if df.empty:
            return None, None, "لا توجد بيانات متاحة حالياً"

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        close = df['Close']
        
        # المؤشرات الفنية
        df['SMA_20'] = SMAIndicator(close=close, window=20).sma_indicator()
        df['EMA_50'] = EMAIndicator(close=close, window=50).ema_indicator()
        df['RSI'] = RSIIndicator(close=close, window=14).rsi_indicator()
        
        macd_obj = MACD(close=close)
        df['MACD'] = macd_obj.macd()
        df['MACD_Signal'] = macd_obj.macd_signal()

        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        current_price = latest['Close']
        price_change = current_price - prev['Close']

        # حساب التوصية
        score = 0
        if current_price > latest['SMA_20'] and current_price > latest['EMA_50']:
            score += 2
        elif current_price < latest['SMA_20'] and current_price < latest['EMA_50']:
            score -= 2
            
        if latest['RSI'] < 30:
            score += 3
        elif latest['RSI'] > 70:
            score -= 3
            
        if latest['MACD'] > latest['MACD_Signal'] and prev['MACD'] <= prev['MACD_Signal']:
            score += 2
        elif latest['MACD'] < latest['MACD_Signal'] and prev['MACD'] >= prev['MACD_Signal']:
            score -= 2

        if score >= 3:
            rec, color, desc = "شراء (Buy)", "green", "الاتجاه صاعد مع إشارات إيجابية قوية."
        elif score <= -3:
            rec, color, desc = "بيع (Sell)", "red", "الاتجاه هابط مع وجود ضغط بيعي قوي."
        else:
            rec, color, desc = "محايد (Hold)", "orange", "السوق في حالة تذبذب، يفضل الانتظار."

        analysis = {
            'price': current_price,
            'change': price_change,
            'rsi': latest['RSI'],
            'recommendation': rec,
            'color': color,
            'desc': desc
        }
        return df, analysis, None
    except Exception as e:
        return None, None, str(e)

# 3. عرض علامات التبويب (الذهب والفضة الفورية)
tab_gold, tab_silver = st.tabs(["🥇 الذهب (XAU)", "🥈 الفضة (XAG)"])

GOLD_SYMBOL = "XAUUSD=X"
SILVER_SYMBOL = "XAGUSD=X"

def render_market_view(symbol, name):
    df, analysis, error = get_market_data(symbol)
    
    if error or df is None:
        st.error(f"تعذر جلب بيانات {name}. يرجى محاولة التحديث.")
        return

    st.metric(label=f"سعر {name} الحالي (Spot)", value=f"${analysis['price']:.2f}", delta=f"{analysis['change']:+.2f}")

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
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='orange', width=1), name="SMA 20"))
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_50'], line=dict(color='lightblue', width=1), name="EMA 50"))

    fig.update_layout(
        margin=dict(l=5, r=5, t=5, b=5),
        height=300,
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

with tab_gold:
    render_market_view(GOLD_SYMBOL, "الذهب")

with tab_silver:
    render_market_view(SILVER_SYMBOL, "الفضة")

if st.button("🔄 تحديث البيانات"):
    st.cache_data.clear()
    st.rerun()
