import os
import random
import time
import streamlit.components.v1 as components
import streamlit as st
from openai import OpenAI

# ==========================================
# 1. إعدادات الصفحة
# ==========================================
st.set_page_config(
    page_title="محلل ومستشار الذهب والفضة (XAUUSD/XAGUSD)",
    page_icon="📈",
    layout="wide",
)

# ==========================================
# 2. إعداد عميل Groq باستخدام مكتبة OpenAI
# ==========================================
GROQ_API_KEY = st.secrets.get(
    "GROQ_API_KEY",
    os.getenv(
        "GROQ_API_KEY",
        "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",  # مفتاحك
    ),
)

client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)


# ==========================================
# 3. محاكي القراءات الحية للسوق (Live Market Feed)
# ==========================================
def get_live_market_data():
    # محاكاة السعر الحي للذهب بناءً على النطاق الحالي (مثلاً حول 4,140)
    base_price = 4140.50
    current_price = round(
        base_price + random.uniform(-3.5, 3.5), 2
    )  # السعر يتغير لححظياً
    change = round(random.uniform(-1.2, 1.5), 2)
    rsi_val = random.randint(35, 72)  # مؤشر القوة النسبية

    if rsi_val > 65:
        momentum = "تشبع شرائي (Overbought) ⚠️"
    elif rsi_val < 40:
        momentum = "تشبع بيعي (Oversold) ⚠️"
    else:
        momentum = "استقرار وتذبذب عرضي ⚖️"

    return {
        "price": current_price,
        "change": change,
        "rsi": rsi_val,
        "momentum": momentum,
    }


# جلب قراءة السوق الحالية
market = get_live_market_data()


# ==========================================
# 4. دالة التوصيات الذكية التلقائية
# ==========================================
def get_auto_ai_advice(market_data):
    prompt = f"""
    بصفتك خبير سكالبينج وتحليل فني للذهب (XAUUSD)، إليك القراءات الحية الحالية للسوق:
    - السعر الحالي: {market_data['price']}
    - نسبة التغير: {market_data['change']}%
    - مؤشر القوة النسبية (RSI): {market_data['rsi']}
    - حالة الزخم: {market_data['momentum']}

    قدم نصيحة وتوصية تداول فورية وموجزة جداً (في حدود أسطر معدودة) تتضمن:
    1. الإشارة (شراء 🟢 / بيع 🔴 / انتظار ⏳).
    2. السبب الفني السريع بناءً على الأرقام الحالية.
    """

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "أنت مستشار مالي آلي يقدم توصيات سكالبينج لحظية ومباشرة."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception as e:
        return "⚠️️ تعذر جلب التوصية الآلية حالياً."


# ==========================================
# 5. الشريط الجانبي (Sidebar) - التوصيات الحية والشات
# ==========================================
with st.sidebar:
    st.subheader("🤖 التوصيات الآلية الحية (Live AI)")

    # عرض بطاقة الأسعار والقراءات الحية في الشريط الجانبي
    st.markdown(
        f"""
    * **السعر المباشر:** `{market['price']} $`
    * **التغير:** `{market['change']}%`
    * **مؤشر RSI:** `{market['rsi']}`
    * **الحالة:** `{market['momentum']}`
    """
    )

    if st.button("🔄 تحديث التحليل والنصائح الآن"):
        st.rerun()

    st.markdown("---")

    # جلب وعرض النصيحة المستمرة من الذكاء الاصطناعي بناءً على السعر الحي
    with st.spinner("جاري تحليل القراءات الحية..."):
        live_advice = get_auto_ai_advice(market)
    st.info(live_advice)

    st.markdown("---")
    st.subheader("💬 محادثة المستشار الخاص")

    # تهيئة سجل المحادثة
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "مرحباً بك! أنا أراقب الأسعار الحية للذهب معك. اسألني أي"
                    " شيء عن السوق!"
                ),
            }
        ]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_input = st.chat_input("اطرح سؤالك أو اطلب صفقة...")

    if user_input:
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("assistant"):
            with st.spinner("جاري الرد..."):
                # دالة العادية للدردشة
                messages_payload = [
                    {
                        "role": "system",
                        "content": "أنت مستشار مالي محترف للذهب والفضة.",
                    }
                ]
                for msg in st.session_state.messages:
                    messages_payload.append(
                        {"role": msg["role"], "content": msg["content"]}
                    )

                response = client.chat.completions.create(
                    model="openai/gpt-oss-20b",
                    messages=messages_payload,
                    temperature=0.3,
                )
                ai_reply = response.choices[0].message.content
                st.markdown(ai_reply)

        st.session_state.messages.append(
            {"role": "assistant", "content": ai_reply}
        )


# ==========================================
# 6. الواجهة الرئيسية (شاشة مراقبة الشارت)
# ==========================================
st.title("📈 محطة تحليل الذهب والفضة & الشاشة الحية")

# تضمين شارت TradingView الاحترافي
tradingview_widget_html = """
<!-- TradingView Widget BEGIN -->
<div class="tradingview-widget-container" style="height:620px;width:100%">
  <div id="tradingview_chart" style="height:100%;width:100%"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
  <script type="text/javascript">
  new TradingView.widget(
  {
  "width": "100%",
  "height": "620",
  "symbol": "OANDA:XAUUSD",
  "interval": "5",
  "timezone": "Etc/UTC",
  "theme": "dark",
  "style": "1",
  "locale": "ar",
  "toolbar_bg": "#f1f3f6",
  "enable_publishing": false,
  "hide_side_toolbar": false,
  "allow_symbol_change": true,
  "details": true,
  "hotlist": true,
  "calendar": false,
  "container_id": "tradingview_chart"
  }
  );
  </script>
</div>
<!-- TradingView Widget END -->
"""
components.html(tradingview_widget_html, height=640)
