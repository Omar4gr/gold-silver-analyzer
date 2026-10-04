import datetime
import random
import streamlit.components.v1 as components
import streamlit as st

# ==========================================
# 1. إعدادات الصفحة
# ==========================================
st.set_page_config(
    page_title="محلل ومستشار الذهب والفضة", page_icon="📈", layout="wide"
)

# ==========================================
# 2. التحقق من أوقات العمل الرسمية (بتوقيت العراق)
# ==========================================
utc_now = datetime.datetime.utcnow()
iraq_now = utc_now + datetime.timedelta(hours=3)
weekday = iraq_now.weekday()  # 5=السبت, 6=الأحد

if weekday == 5 or weekday == 6:
    market_status = "السوق مغلق (عطلة نهاية الأسبوع) 🔴"
    reopen_msg = (
        "⏳ موعد الافتتاح: يفتح السوق رسمياً يوم الإثنين الساعة 1:00 فجراً بتوقيت"
        " بغداد"
    )
    advice_text = (
        "السوق مغلق حالياً بسبب عطلة نهاية الأسبوع. ترقب فجوات الافتتاح (Gap)"
        " عند العودة يوم الإثنين واحرص على إدارة المخاطر."
    )
else:
    market_status = "السوق مفتوح ويشهد تداولاً حيّاً 🟢"
    reopen_msg = ""
    advice_text = (
        "التوصية الحالية: راقب مستويات الدعم والمقاومة الحية على الشارت،"
        " واستخدم استراتيجيات السكالبينج بحذر."
    )

# ==========================================
# 3. الشريط الجانبي (Sidebar)
# ==========================================
with st.sidebar:
    st.subheader("🤖 حالة السوق والتوقعات")

    st.markdown(f"**حالة السوق:** {market_status}")

    if reopen_msg:
        st.warning(reopen_msg)
    else:
        st.markdown(f"**السعر المباشر:** `4,140.50 $`")
        st.markdown(f"**التغير:** `+1.35%`")

    if st.button("🔄 تحديث التحليل"):
        st.rerun()

    st.markdown("---")
    st.markdown("### 💡 التوصية الحالية")
    st.markdown(advice_text)

    st.markdown("---")
    st.subheader("💬 محادثة المستشار الخاص")

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "مرحباً بك! أنا أتابع السوق معك. اسألني أي وقت عن التحليل."
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

        ai_reply = f"لقد استلمت سؤالك حول ({user_input}). نظراً لأن السوق في حالة ترقب، أنصحك بمراقبة حركة السعر الحية على الشارت."
        with st.chat_message("assistant"):
            st.markdown(ai_reply)
        st.session_state.messages.append(
            {"role": "assistant", "content": ai_reply}
        )

# ==========================================
# 4. الواجهة الرئيسية (شاشة الشارت)
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
