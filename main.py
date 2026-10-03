import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator
from streamlit_autorefresh import st_autorefresh

# 1. إعدادات الصفحة (يجب أن تكون أول أمر Streamlit في الملف)
st.set_page_config(
    page_title="محلل الذهب والفضة الذكي",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 2. التحديث التلقائي كل 10 ثانية
st_autorefresh(interval=10000, key="data_refresh")

# 3. تنسيق CSS
st.markdown("""
    <style>
    .stApp {
        max-width: 100%;
        margin: 0 auto;
    }
    .ai-box {
        background-color: #1a233a;
        border-right: 5px solid #2962ff;
        padding: 15px;
        border-radius: 8px;
        margin-top: 10px;
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📈 محلل الأسواق الذكي")
st.caption("رسوم بيانية تفاعلية وتحليل بالذكاء الاصطناعي للذهب والفضة")

@st.cache_data(ttl=30)
def fetch_data_and_analyze(ticker_symbol, period="30d", interval="1h"):
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            return None, None

        # حساب المؤشرات الفنية
        df['SMA_20'] = SMAIndicator(close=df['Close'], window=20).sma_indicator()
        df['EMA_50'] = EMAIndicator(close=df['Close'], window=50).ema_indicator()
        df['RSI'] = RSIIndicator(close=df['Close'], window=14).rsi()
        
        macd = MACD(close=df['Close'])
        df['MACD'] = macd.macd()
        df['MACD_Signal'] = macd.macd_signal()

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        score = 0
        reasons = []

        # 1. المتوسطات المتحركة
        if latest['Close'] > latest['SMA_20'] > latest['EMA_50']:
            score += 2
            reasons.append("السعر أعلى من المتوسطات 20 و 50 (اتجاه صاعد قوي)")
        elif latest['Close'] < latest['SMA_20'] < latest['EMA_50']:
            score -= 2
            reasons.append("السعر أسفل المتوسطات (اتجاه هابط ضاغط)")

        # 2. مؤشر RSI
        rsi_val = latest['RSI']
        if rsi_val < 30:
            score += 3
            reasons.append(f"مؤشر RSI منخفض جداً ({round(rsi_val,1)}) - تشبع بيعي وفرصة ارتداد أعلى")
        elif rsi_val > 70:
            score -= 3
            reasons.append(f"مؤشر RSI مرتفع جداً ({round(rsi_val,1)}) - تشبع شرائي واحتمال تصحيح للهبوط")
        else:
            reasons.append(f"مؤشر RSI متوازن ({round(rsi_val,1)})")

        # 3. تقاطع MACD
        if prev['MACD'] < prev['MACD_Signal'] and latest['MACD'] > latest['MACD_Signal']:
            score += 2
            reasons.append("حدث تقاطع إيجابي لمؤشر MACD (إشارة دخول شراء)")
        elif prev['MACD'] > prev['MACD_Signal'] and latest['MACD'] < latest['MACD_Signal']:
            score -= 2
            reasons.append("حدث تقاطع سلبي لمؤشر MACD (إشارة خروج/بيع)")

        # القرار النهائي
        if score >= 3:
            decision = "🟢 الوقت مناسب للشراء (Buy Signal)"
            confidence = "عالية"
        elif score <= -3:
            decision = "🔴 الوقت مناسب للبيع / جني الأرباح (Sell Signal)"
            confidence = "عالية"
        else:
            decision = "🟡 محايد - يفضل الانتظار والمراقبة (Hold)"
            confidence = "متوسطة"

        ai_analysis = {
            "price": round(latest['Close'], 2),
            "change": round(latest['Close'] - df.iloc[0]['Close'], 2),
            "rsi": round(rsi_val, 2),
            "decision": decision,
            "confidence": confidence,
            "reasons": reasons
        }

        return df, ai_analysis
    except Exception:
        return None, None

def create_candlestick_chart(df, name):
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name="السعر"
    ))

    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], mode='lines', name='SMA 20', line=dict(color='orange', width=1)))
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_50'], mode='lines', name='EMA 50', line=dict(color='lightblue', width=1)))

    fig.update_layout(
        title=f"رسم بياني تفاعلي - {name}",
        yaxis_title="السعر ($)",
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        margin=dict(l=10, r=10, t=40, b=10),
        height=400
    )
    return fig

if st.button("تحديث يدوي الآن 🔄", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.write("")

tab1, tab2 = st.tabs(["🥇 الذهب (XAU)", "🥈 الفضة (XAG)"])

with tab1:
    df_gold, ai_gold = fetch_data_and_analyze("GC=F")
    if ai_gold:
        st.metric(label="سعر الذهب الحالي", value=f"${ai_gold['price']}", delta=f"${ai_gold['change']}")
        
        st.markdown(f"""
        <div class="ai-box">
            <h4>🤖 توصية مستشار الذكاء الاصطناعي:</h4>
            <h3>{ai_gold['decision']}</h3>
            <p><b>درجة الثقة:</b> {ai_gold['confidence']}</p>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("🔍 أسباب التوصية والتحليل الفني التفصيلي"):
            for reason in ai_gold['reasons']:
                st.write(f"- {reason}")

        fig = create_candlestick_chart(df_gold, "الذهب")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("تعذر جلب بيانات الذهب حالياً، يرجى إعادة المحاولة.")

with tab2:
    df_silver, ai_silver = fetch_data_and_analyze("SI=F")
    if ai_silver:
        st.metric(label="سعر الفضة الحالي", value=f"${ai_silver['price']}", delta=f"${ai_silver['change']}")
        
        st.markdown(f"""
        <div class="ai-box">
            <h4>🤖 توصية مستشار الذكاء الاصطناعي:</h4>
            <h3>{ai_silver['decision']}</h3>
            <p><b>درجة الثقة:</b> {ai_silver['confidence']}</p>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("🔍 أسباب التوصية والتحليل الفني التفصيلي"):
            for reason in ai_silver['reasons']:
                st.write(f"- {reason}")

        fig = create_candlestick_chart(df_silver, "الفضة")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("تعذر جلب بيانات الفضة حالياً، يرجى إعادة المحاولة.")