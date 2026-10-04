import datetime
import os
import random
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
# 3. التحقق من أوقات العمل الرسمية (بتوقيت العراق المحلي بدون مكتبات خارجية)
# ==========================================
def check_market_status():
    # توقيت العراق يوافق UTC+3
    utc_now = datetime.datetime.utcnow()
    iraq_now = utc_now + datetime.timedelta(hours=3)
    weekday = iraq_now.weekday()  # 0=الإثنين, ..., 5=السبت, 6=الأحد
    hour = iraq_now.hour

    # أسواق الفوركس تغلق السبت وتفتح فجر الإثنين (الساعة 01:00 بتوقيت بغداد)
    if weekday == 5:  # يوم السبت (مغلق بالكامل)
        return {
            "is_open": False,
            "status_text": "السوق مغلق (عطلة نهاية الأسبوع) 🔴",
            "reopen_time": "يفتح السوق رسمياً يوم الإثنين الساعة 1:00 فجراً بتوقيت بغداد",
        }
    elif weekday == 6:  # يوم الأحد
        if (
            hour < 1
        ):  # الساعات الأولى من الأحد تعتبر امتداد لعطلة السبت أو إغلاق الأسبوع
            return {
                "is_open": False,
                "status_text": "السوق مغلق (عطلة نهاية الأسبوع) 🔴",
                "reopen_time": (
                    "يفتح السوق رسمياً يوم الإثنين الساعة 1:00 فجراً بتوقيت بغداد"
                ),
            }
        else:
            return {
                "is_open": False,
                "status_text": "السوق مغلق (عطلة نهاية الأسبوع) 🔴",
                "reopen_time": (
                    "يفتح السوق رسمياً يوم الإثنين الساعة 1:00 فجراً بتوقيت بغداد"
                ),
            }
    elif weekday == 0 and hour < 1:  # فجر الإثنين قبل الساعة 1:00
        return {
            "is_open": False,
            "status_text": "السوق مغلق وقارب على الافتتاح ⏳",
            "reopen_time": "يفتح السوق اليوم الساعة 1:00 فجراً بتوقيت بغداد",
        }
    else:
        return {
            "is_open": True,
            "status_text": "السوق مفتوح ويشهد تداولاً حيّاً 🟢",
            "reopen_time": "",
        }


market_status = check_market_status()


# ==========================================
# 4. محاكي الأسعار والتوقعات
# ==========================================
def get_live_market_data():
    base_price = 4140.50
    current_price = round(base_price + random.uniform(-3.5, 3.5), 2)
    change = round(random.uniform(-1.2, 1.5), 2)
    rsi_val = 40

    return {
        "price": current_price,
        "change": change,
        "rsi": rsi_val,
        "momentum": "استقرار وترقب الافتتاح ⚖️",
    }


market = get_live_market_data()


# ==========================================
# 5. دالة التوصيات والتوقعات الذكية
# ==========================================
def get_auto_ai_advice(market_data, status):
    if not status["is_open"]:
        prompt = f"""
        السوق حالياً مغلق (عطلة نهاية الأسبوع)، وسيعود للفتح يوم الإثنين الساعة 1:00 فجراً بتوقيت بغداد.
        آخر إغلاق للذهب (XAUUSD) كان حول السعر: {market_data['price']}.
        بصفتك محللاً فنياً محترفاً، قدم توقعات استباقية ونظرة تحليلية قصيرة جداً لما يمكن أن يبدأ به السوق عند الافتتاح وكيف يتعامل المتداول مع فجوات الافتتاح (Gap).
        """
    else:
        prompt = f"""
        السوق مفتوح. السعر الحالي: {market_data['price']}، التغير: {market_data['change']}%، RSI: {market_data['rsi']}.
        قدم توصية سكالبينج سريعة ومباشرة.
        """

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "أنت مستشار مالي وخبير تداول للذهب والفضة."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception as e:
        return "⚠ تعذر جلب التوصية حالياً."


# ==========================================
# 6. الشريط الجانبي (Sidebar)
# ==========================================
with st.sidebar:
    st.subheader("🤖 حالة السوق والتوقعات (Live AI)")

    st.markdown(f"* **حالة السوق:** `{market_status['status_text']}`")

    if not market_status["is_open"]:
        st.warning(f"⏳ **موعد الافتتاح:** {market_status['reopen_time']}")
    else:
        st.markdown(f"* **السعر المباشر:** `{market['price']} $`")
        st.markdown(f"* **التغير:** `{market['change']}%`")

    if st.button("🔄 تحديث التحليل والتوقعات"):
        st.rerun()

    st.markdown("---")

    with st.spinner("جاري تحليل حالة السوق..."):
        live_advice = get_auto_ai_advice(market, market_status)
    st.info(live_advice)

    st.markdown("---")
    st.subheader("💬 محادثة المستشار الخاص")

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "مرحباً بك! أنا أتابع أوقات وأيام عمل السوق معك. اسألني"
                    " عن أي استراتيجية أو تحليل!"
                ),
            }
        ]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_input = st.chat_input("اطرح سؤالك هنا...")

    if user_input:
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("assistant"):
            with st.spinner("جاري الرد..."):
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
# 7. الواجهة الرئيسية (شاشة الشارت)
# ==========================================
st.title("📈 محطة تحليل الذهب والفضة & الشاشة الحية")

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
