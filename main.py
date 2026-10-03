import json
import os
import requests
import streamlit as st

# ==========================================
# 1. إعدادات الصفحة
# ==========================================
st.set_page_config(
    page_title="محلل ومستشار الذهب والفضة (XAUUSD/XAGUSD)",
    page_icon="📈",
    layout="wide",
)

# ==========================================
# 2. الحصول على مفتاح Groq API
# ==========================================
GROQ_API_KEY = st.secrets.get(
    "GROQ_API_KEY",
    os.getenv(
        "GROQ_API_KEY",
        "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",  # مفتاح Groq الخاص بك
    ),
)


# ==========================================
# 3. دالة الاتصال بـ Groq AI Advisor
# ==========================================
def ask_ai_advisor(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    # تجهيز سجل المحادثة كـ Messages
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

    # إضافة سجل المحادثة السابق للحفاظ على سياق الحوار
    for msg in st.session_state.get("messages", []):
        messages.append({"role": msg["role"], "content": msg["content"]})

    # إضافة السؤال الحالي
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": "llama-3.1-8b-instant",  # النموذج الأقوى والأكثر استقراراً وسرعة على Groq
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 500,
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            return f"❌ خطأ من الخادم ({response.status_code}): {response.text}"
    except Exception as e:
        return f"❌ تعذر الاتصال بالخدمة: {str(e)}"


# ==========================================
# 4. الواجهة الرئيسية والتفاعل (Streamlit)
# ==========================================
st.title("📈 محطة تحليل الذهب والفضة & المستشار الذكي")

# --- قسم الرسم البياني والبيانات ---
st.subheader("📊 حركة الأسعار")

st.markdown("---")

# --- قسم محادثة مستشار الذكاء الاصطناعي ---
st.subheader("💬 محادثة مستشار الذكاء الاصطناعي")

# تهيئة سجل المحادثة في Session State
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

# عرض جميع الرسائل السابقة في الواجهة
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# استقبال مدخلات المستخدم
user_input = st.chat_input("أسأل الذكاء الاصطناعي: اشتري ولا أبيع؟")

if user_input:
    # عرض رسالة المستخدم فوراً
    with st.chat_message("user"):
        st.markdown(user_input)

    # حفظ رسالة المستخدم في السجل
    st.session_state.messages.append({"role": "user", "content": user_input})

    # جلب الإجابة من Groq مع إظهار مؤشر التحميل
    with st.chat_message("assistant"):
        with st.spinner("جاري تحليل البيانات وإعداد التوصية..."):
            ai_response = ask_ai_advisor(user_input)
            st.markdown(ai_response)

    # حفظ إجابة الذكاء الاصطناعي في السجل
    st.session_state.messages.append(
        {"role": "assistant", "content": ai_response}
    )
