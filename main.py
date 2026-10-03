import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator
from streamlit_autorefresh import st_autorefresh

# ---------------------------------------------------------
# 1. إعدادات الصفحة والتصميم المخصص للهواتف والـ APK
# ---------------------------------------------------------
st.set_page_config(
    page_title="محلل الأسواق الذكي",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# تحديث تلقائي كل 30 ثانية
st_autorefresh(interval=30000, key="datarefresh")

# تنسيق CSS احترافي لإلغاء الحواف المزعجة وإخفاء القوائم الجانبية
st.markdown("""
    <style>
    /* إخفاء القائمة الجانبية والشريط العلوي الافتراضي لـ Streamlit */
    [data-testid="stSidebar"] { display: none; }
    [data-testid="collapsedControl"] { display: none; }
    header { visibility: hidden; height: 0px !important; }
    footer { visibility: hidden; height: 0px !important; }
    
    /* ضبط الحواف والمساحات الخارجية لملء الشاشة بالكامل */
    .block-container {
        padding-top: 0.8rem !important;
        padding-bottom: 0.5rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        max-width: 100% !important;
    }
    
    /* تحسين شكل العنوان والعناوين الفرعية */
    .main-title {
        text-align: center;
        font-size: 1.6rem;
        font-weight: bold;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        text-align: center;
        font-size: 0.85rem;
        color: #888;
        margin-bottom: 0.8rem;
    }
    
    /* تنسيق أزرار التبويب Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        justify-content: center;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
        border-radius: 8px;
        font-weight: bold;
    }
    
    /* تحسين شكل التوصية */
    .stAlert {
        font-size: 0.9rem !important;
        border-radius: 10px !important;
        padding: 10px !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">📈 محلل الأسواق الذكي</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">تحليل فني وتوصيات ذكية لحظية للذهب والفضة</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. دالة جلب البيانات والتحليل الفني
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

        # خوارزمية حساب التوصية
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
# 3. عرض البيانات والشاشات
# ---------------------------------------------------------
tab_gold, tab_silver = st.tabs(["🥇 الذهب (XAUUSD)", "🥈 الفضة (XAGUSD)"])

def render_market_view(symbol_type, name):
    df, analysis, error = get_market_data(symbol_type)
    
    if error or df is None:
        st.error(f"تعذر جلب بيانات {name}: {error}")
        return

    # عرض السعر والتغير
    st.metric(
        label=f"سعر {name} الحالي (Spot)", 
        value=f"${analysis['price']:.2f}", 
        delta=f"{analysis['change']:+.2f}"
    )

    # عرض مربع التوصية
    rec_text = f"**توصية الذكاء الاصطناعي:** {analysis['recommendation']}\n\n_{analysis['desc']}_"
    if analysis['color'] == "green":
        st.success(rec_text)
    elif analysis['color'] == "red":
        st.error(rec_text)
    else:
        st.warning(rec_text)

    # الرسم البياني المخصص للتطبيقات المحمولة
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="السعر"
    ))
    if 'SMA_20' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='orange', width=1), name="SMA 20"))
    if 'EMA_50' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['EMA_50'], line=dict(color='#00d2ff', width=1), name="EMA 50"))

    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        height=380,
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

with tab_gold:
    render_market_view("gold", "الذهب")

with tab_silver:
    render_market_view("silver", "الفضة")

# زر التحديث في الأسفل بصورة مدمجة
if st.button("🔄 تحديث الأسعار والتحليل"):
    st.cache_data.clear()
    st.rerun()
