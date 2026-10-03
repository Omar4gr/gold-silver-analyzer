import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator, StochasticOscillator
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
    [data-testid="stSidebar"] { display: none; }
    [data-testid="collapsedControl"] { display: none; }
    header { visibility: hidden; height: 0px !important; }
    footer { visibility: hidden; height: 0px !important; }
    
    .block-container {
        padding-top: 0.8rem !important;
        padding-bottom: 0.5rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        max-width: 100% !important;
    }
    
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
    
    .stTabs [data-baseweb="tab-list"] { gap: 8px; justify-content: center; }
    .stTabs [data-baseweb="tab"] { padding: 8px 16px; border-radius: 8px; font-weight: bold; }
    
    .stAlert { font-size: 0.9rem !important; border-radius: 10px !important; padding: 10px !important; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">📈 محلل الصفقات السريعة (Scalping)</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">توصيات لحظية وإدارة مخاطر بالدولار الأمريكي ($ USD)</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. إدخال رأس المال بالدولار فقط
# ---------------------------------------------------------
capital_usd = st.number_input(
    "💰 كم تملك رأس مال للتداول؟ ($ USD):", 
    min_value=1.0, 
    value=1000.0, 
    step=50.0,
    format="%.2f"
)

# ---------------------------------------------------------
# 3. دالة جلب البيانات والتحليل اللحظي
# ---------------------------------------------------------
@st.cache_data(ttl=15)
def get_market_data(symbol_type, capital_usd):
    # استخدام أسعار الذهب والفضة الفورية (Spot USD)
    symbol = "XAUUSD=X" if symbol_type == "gold" else "XAGUSD=X"
    fallback_symbol = "GC=F" if symbol_type == "gold" else "SI=F"
    
    df = pd.DataFrame()
    last_error = ""

    try:
        data = yf.Ticker(symbol).history(period="1d", interval="1m")
        if not data.empty and len(data) > 5:
            df = data
        else:
            data_fallback = yf.Ticker(fallback_symbol).history(period="5d", interval="5m")
            if not data_fallback.empty:
                df = data_fallback
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

        # المؤشرات الفنية للتحليل السريع (Scalping)
        df['SMA_20'] = SMAIndicator(close=close, window=min(20, len(df))).sma_indicator()
        df['EMA_50'] = EMAIndicator(close=close, window=min(50, len(df))).ema_indicator()
        df['RSI'] = RSIIndicator(close=close, window=14).rsi()
        
        stoch = StochasticOscillator(high=df['High'], low=df['Low'], close=close, window=14, smooth_window=3)
        df['Stoch_K'] = stoch.stoch()

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        current_price = float(latest['Close'])
        price_change = float(current_price - prev['Close'])

        # حساب تقييم الحركة (Score)
        score = 0
        if current_price > latest.get('SMA_20', current_price): score += 1
        else: score -= 1

        rsi_val = latest.get('RSI', 50)
        if rsi_val < 35: score += 2      # تشبع بيعي - إشارة صعود
        elif rsi_val > 65: score -= 2    # تشبع شرائي - إشارة هبوط

        stoch_k = latest.get('Stoch_K', 50)
        if stoch_k < 20: score += 2
        elif stoch_k > 80: score -= 2

        # تحديد حجم الدخول وإدارة المخاطر بالدولار
        if score >= 3:
            rec = "شراء سريع (Scalp Buy 🟢)"
            color = "green"
            desc = "صعود لحظي متوقع! إشارات زخم إيجابية."
            invest_ratio = 0.08  # استثمار 8% من رأس المال
            tp_perc = 0.005      # هدف ربح 0.5%
            sl_perc = 0.003      # وقف خسارة 0.3%
        elif score <= -3:
            rec = "بيع سريع (Scalp Sell 🔴)"
            color = "red"
            desc = "هبوط لحظي متوقع! ضغط بيعي واستكمال هبوط."
            invest_ratio = 0.08  # 8%
            tp_perc = 0.005
            sl_perc = 0.003
        elif score in [1, 2]:
            rec = "شراء خفيف (Weak Buy 🟡)"
            color = "orange"
            desc = "إشارة صعود بسيطة، ينصح بالدخول بمبلغ صغير."
            invest_ratio = 0.03  # 3% فقط
            tp_perc = 0.003
            sl_perc = 0.002
        elif score in [-1, -2]:
            rec = "بيع خفيف (Weak Sell 🟡)"
            color = "orange"
            desc = "إشارة هبوط بسيطة، دخول بحذر بمبلغ صغير."
            invest_ratio = 0.03
            tp_perc = 0.003
            sl_perc = 0.002
        else:
            rec = "انتظار (Hold ⚪)"
            color = "orange"
            desc = "السوق غير واضح، تجنب المخاطرة الآن."
            invest_ratio = 0.0
            tp_perc, sl_perc = 0.0, 0.0

        # الحسابات الماليّة بالدولار
        invest_amount = capital_usd * invest_ratio
        expected_profit = invest_amount * tp_perc
        expected_loss = invest_amount * sl_perc

        if "شراء" in rec:
            tp_price = current_price * (1 + tp_perc)
            sl_price = current_price * (1 - sl_perc)
        else:
            tp_price = current_price * (1 - tp_perc)
            sl_price = current_price * (1 + sl_perc)

        analysis = {
            'price': current_price,
            'change': price_change,
            'recommendation': rec,
            'color': color,
            'desc': desc,
            'invest_amount': invest_amount,
            'invest_percent': invest_ratio * 100,
            'expected_profit': expected_profit,
            'expected_loss': expected_loss,
            'tp_price': tp_price,
            'sl_price': sl_price
        }

        return df, analysis, None
    except Exception as e:
        return None, None, str(e)

# ---------------------------------------------------------
# 4. واجهة العرض
# ---------------------------------------------------------
tab_gold, tab_silver = st.tabs(["🥇 الذهب (XAUUSD)", "🥈 الفضة (XAGUSD)"])

def render_market_view(symbol_type, name):
    df, analysis, error = get_market_data(symbol_type, capital_usd)
    
    if error or df is None:
        st.error(f"تعذر جلب بيانات {name}: {error}")
        return

    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            label=f"سعر {name} (أونصة)", 
            value=f"${analysis['price']:.2f}", 
            delta=f"{analysis['change']:+.2f} $"
        )
    with col2:
        st.metric(
            label="مبلغ الصفقة المقترح", 
            value=f"${analysis['invest_amount']:,.2f}", 
            delta=f"{analysis['invest_percent']:.1f}% من رأس المال"
        )

    # تفاصيل الصفقة والأهداف بالدولار
    rec_box = f"### {analysis['recommendation']}\n\n" \
              f"📌 **التحليل اللحظي:** {analysis['desc']}\n\n" \
              f"💵 **المبلغ الموصى بالدخول به:** `${analysis['invest_amount']:,.2f}`\n\n" \
              f"🎯 **الربح المتوقع بالصفقة:** `+${analysis['expected_profit']:.2f}` (عند سعر ${analysis['tp_price']:.2f})\n\n" \
              f"🛑 **أقصى خسارة مسموح بها:** `-${analysis['expected_loss']:.2f}` (عند سعر ${analysis['sl_price']:.2f})"

    if analysis['color'] == "green":
        st.success(rec_box)
    elif analysis['color'] == "red":
        st.error(rec_box)
    else:
        st.warning(rec_box)

    # الرسم البياني
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
        height=340,
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

with tab_gold:
    render_market_view("gold", "الذهب")

with tab_silver:
    render_market_view("silver", "الفضة")

if st.button("🔄 تحديث التحليل"):
    st.cache_data.clear()
    st.rerun()
