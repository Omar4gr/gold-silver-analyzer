import os
import streamlit.components.v1 as components
import streamlit as strlit_ui  # للاستخدام الداخلي بدون تأثير
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

# تهيئة العميل الموجه نحو خوادم Groq
client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)


# ==========================================
# 3. دالة المحادثة والتحليل (كما هي تماماً بدون أي تغيير)
# ==========================================
def ask_ai_advisor(prompt):
    messages = [
        {
            "role": "system",
            "content": (
                "أنت مستشار مالي وخبير تداول محترف متخصص في السكالبينج"
                " والتحليل الفني للذهب والفضة (XAUUSD / XAGUSD). إجاباتك موجزة،"
                " دقيقة، مباشرة، وتقدم توصيات واضحة بناءً على حركة الأسعار"
                " والمؤشرات."
            ),
        }
    ]

    for msg in st.session_state.get("messages", []):
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": prompt})

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b", messages=messages, temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ حدث خطأ في الاتصال: {str(e)}"


# ==========================================
# 4. واجهة التطبيق
# ==========================================
st.title("📈 محطة تحليل الذهب والفضة & المستشار الذكي")

# --- قسم حركة الأسعار (شارت احترافي شبيه بـ TradingView) ---
st.subheader("📊 حركة الأسعار (XAUUSD)")

# تضمين شارت تفاعلي حقيقي لأسعار الذهب (TradingView Advanced Real-time Widget)
tradingview_widget_html = """
<!-- TradingView Widget BEGIN -->
<div class="tradingview-widget-container" style="height:450px;width:100%">
  <div id="tradingview_chart" style="height:100%;width:100%"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
  <script type="text/javascript">
  new TradingView.widget(
  {
  "width": "100%",
  "height": "450",
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
components.html(tradingview_widget_html, height=470)

st.markdown("---")

# --- قسم محادثة مستشار الذكاء الاصطناعي (كما هو تماماً) ---
st.subheader("💬 محادثة مستشار الذكاء الاصطناعي")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "مرحباً بك! أنا مستشارك المالي المباشر لصفقات الذهب والفضة"
                " (XAUUSD/XAGUSD). كيف يمكنني مساعدتك في تحليلك اليوم؟"
            ),
        }
    ]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_input = st.chat_input("أسأل الذكاء الاصطناعي: اشتري ولا أبيع؟")

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("assistant"):
        with st.spinner("جاري تحليل البيانات وإعداد التوصية..."):
            ai_response = ask_ai_advisor(user_input)
            st.markdown(ai_response)

    st.session_state.messages.append(
        {"role": "assistant", "content": ai_response}
    )
