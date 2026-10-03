import os
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
# 3. دالة المحادثة والتحليل
# ==========================================
def ask_ai_advisor(prompt):
    # تجهيز سجل المحادثة
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
        # استخدام النموذج القياسي المستقر والثابت دائماً على Groq
        response = client.chat.completions.create(
            model="llama3-70b-8192", messages=messages, temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ حدث خطأ في الاتصال: {str(e)}"


# ==========================================
# 4. واجهة التطبيق
# ==========================================
st.title("📈 محطة تحليل الذهب والفضة & المستشار الذكي")

st.subheader("📊 حركة الأسعار")
st.markdown("---")

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
