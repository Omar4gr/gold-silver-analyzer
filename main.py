import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from ta.trend import SMAIndicator, EMAIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from streamlit_autorefresh import st_autorefresh
from google import genai

# ---------------------------------------------------------
# 1. إعدادات الصفحة والتصميم
# ---------------------------------------------------------
st.set_page_config(
    page_title="محلل الأسواق ومساعد الذكاء الاصطناعي",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# تحديث تلقائي كل 30 ثانية
st_autorefresh(interval=30000, key="datarefresh")

st.markdown("""
    <style>
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

st.markdown('<div class="main-title">📈 محلل الصفقات ومستشار الذكاء الاصطناعي</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">تحليل لحظي بالدولار مع شات بوت ذكي للتوصيات وإدارة رأس المال</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. جلب المفتاح ورأس المال
# ---------------------------------------------------------
api_key = st.secrets.get("GEMINI_API_KEY", "")

with st.sidebar:
    st.header("⚙️ إعدادات التداول")
    if not api_key:
        api_key = st.text_input("أدخل مفتاح Gemini API Key:", type="password")
    
    capital_usd = st.number_input(
        "💰 رأس المال للتداول ($ USD):", 
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

        df['SMA_20'] = SMAIndicator(close=close, window=min(20, len(df))).sma_indicator()
        df['EMA_50'] = EMAIndicator(close=close, window=min(50, len(df))).ema_indicator()
        df['RSI'] = RSIIndicator(close=close, window=14).rsi()
        
        stoch = StochasticOscillator(high=df['High'], low=df['Low'], close=close, window=14, smooth_window=3)
        df['Stoch_K'] = stoch.stoch()

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        current_price = float(latest['Close'])
        price_change = float(current_price - prev['Close'])

        score = 0
        if current_price > latest.get('SMA_20', current_price): score += 1
        else: score -= 1

        rsi_val = latest.get('RSI', 50)
        if rsi_val < 35: score += 2
        elif rsi_val > 65: score -= 2

        stoch_k = latest.get('Stoch_K', 50)
        if stoch_k < 20: score += 2
        elif stoch_k > 80: score -= 2

        if score >= 3:
            rec = "شراء سريع (Scalp Buy 🟢)"
            color = "green"
            desc = "صعود لحظي متوقع! فرصة شراء."
            invest_ratio = 0.08
            tp_perc, sl_perc = 0.005, 0.003
        elif score <= -3:
            rec = "بيع سريع (Scalp Sell 🔴)"
            color = "red"
            desc = "هبوط لحظي متوقع! فرصة بيع."
            invest_ratio = 0.08
            tp_perc, sl_perc = 0.005, 0.003
        elif score in [1, 2]:
            rec = "شراء خفيف (Weak Buy 🟡)"
            color = "orange"
            desc = "إشارة صعود بسيطة، دخول بحذر."
            invest_ratio = 0.03
            tp_perc, sl_perc = 0.003, 0.002
        elif score in [-1, -2]:
            rec = "بيع خفيف (Weak Sell 🟡)"
            color = "orange"
            desc = "إشارة هبوط بسيطة، دخول بحذر."
            invest_ratio = 0.03
            tp_perc, sl_perc = 0.003, 0.002
        else:
            rec = "انتظار (Hold ⚪)"
            color = "orange"
            desc = "السوق غير واضح، تجنب المخاطرة."
            invest_ratio = 0.0
            tp_perc, sl_perc = 0.0, 0.0

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
            'sl_price': sl_price,
            'rsi': rsi_val,
            'stoch': stoch_k
        }

        return df, analysis, None
    except Exception as e:
        return None, None, str(e)

# ---------------------------------------------------------
# 4. عرض الواجهة والرسوم البيانية
# ---------------------------------------------------------
tab_gold, tab_silver = st.tabs(["🥇 الذهب (XAUUSD)", "🥈 الفضة (XAGUSD)"])

active_analysis = {}

def render_market_view(symbol_type, name):
    global active_analysis
    df, analysis, error = get_market_data(symbol_type, capital_usd)
    
    if error or df is None:
        st.error(f"تعذر جلب بيانات {name}: {error}")
        return

    active_analysis[name] = analysis

    col1, col2 = st.columns(2)
    with col1:
        st.metric(label=f"سعر {name}", value=f"${analysis['price']:.2f}", delta=f"{analysis['change']:+.2f} $")
    with col2:
        st.metric(label="المبلغ المقترح للصفقة", value=f"${analysis['invest_amount']:,.2f}", delta=f"{analysis['invest_percent']:.1f}% من المال")

    rec_box = f"### {analysis['recommendation']}\n\n" \
              f"📌 **التحليل:** {analysis['desc']}\n\n" \
              f"🎯 **الربح المتوقع:** `+${analysis['expected_profit']:.2f}` (عند ${analysis['tp_price']:.2f})\n\n" \
              f"🛑 **وقف الخسارة:** `-${analysis['expected_loss']:.2f}` (عند ${analysis['sl_price']:.2f})"

    if analysis['color'] == "green": st.success(rec_box)
    elif analysis['color'] == "red": st.error(rec_box)
    else: st.warning(rec_box)

    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="السعر"))
    if 'SMA_20' in df.columns: fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='orange', width=1), name="SMA 20"))
    if 'EMA_50' in df.columns: fig.add_trace(go.Scatter(x=df.index, y=df['EMA_50'], line=dict(color='#00d2ff', width=1), name="EMA 50"))

    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=300, xaxis_rangeslider_visible=False, template="plotly_dark", showlegend=False)
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

with tab_gold:
    render_market_view("gold", "الذهب")

with tab_silver:
    render_market_view("silver", "الفضة")

# ---------------------------------------------------------
# 5. الشات بوت والمحادثة (باستخدام google-genai)
# ---------------------------------------------------------
st.divider()
st.subheader("💬 محادثة مستشار الذكاء الاصطناعي")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_prompt = st.chat_input("أسأل الذكاء الاصطناعي: اشتري ولا أبيع؟")

if user_prompt:
    st.session_state.chat_history.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    if not api_key:
        bot_response = "⚠️ يُرجى إضافة المفتاح GEMINI_API_KEY في القائمة الجانبية أو في Streamlit Secrets لتفعيل المحادثة."
        with st.chat_message("assistant"):
            st.markdown(bot_response)
        st.session_state.chat_history.append({"role": "assistant", "content": bot_response})
    else:
        with st.chat_message("assistant"):
            with st.spinner("جاري تحليل الأسواق وإعداد التوصية..."):
                try:
                    client = genai.Client(api_key=api_key)
                    
                    prompt_full = f"""
                    أنت خبير تداول ومستشار مالي لحظي للصفقات السريعة (Scalping).
                    رأس مال المستخدم المتاح: {capital_usd}$ USD.
                    
                    بيانات السوق الحالية اللحظية:
                    {active_analysis}
                    
                    سؤال المستخدم: {user_prompt}
                    
                    أجب بوضوح مباشر: هل ينصح بالبيع أم الشراء أم الانتظار الآن؟ وحدد له المبلغ الدقيق للدخول بالدولار وهدف الربح ووقف الخسارة.
                    """
                    
                    available_models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
                    response_text = None
                    last_err = ""

                    for model_name in available_models:
                        try:
                            response = client.models.generate_content(
                                model=model_name,
                                contents=prompt_full,
                            )
                            response_text = response.text
                            break
                        except Exception as e:
                            last_err = str(e)
                            continue

                    if response_text:
                        st.markdown(response_text)
                        st.session_state.chat_history.append({"role": "assistant", "content": response_text})
                    else:
                        st.error(f"تعذر الاتصال بالنماذج. التفاصيل: {last_err}")

                except Exception as e:
                    st.error(f"حدث خطأ في الإعداد: {str(e)}")
