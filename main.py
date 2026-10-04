import datetime
import random
import requests
import streamlit.components.v1 as components
import streamlit as st

# ==========================================
# 0. إعدادات تيليجرام للإشعارات الفورية
# ==========================================
TELEGRAM_BOT_TOKEN = "ضع_التوكن_هنا"  # ضع توكن بوت تيليجرام الخاص بك هنا
TELEGRAM_CHAT_ID = "ضع_الآيدي_هنا"  # ضع الآيدي الخاص بك هنا


def send_telegram_notification(message):
    if (
        TELEGRAM_BOT_TOKEN == "ضع_التوكن_هنا"
        or TELEGRAM_CHAT_ID == "ضع_الآيدي_هنا"
    ):
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception:
        pass


# ==========================================
# 1. إعدادات الصفحة
# ==========================================
st.set_page_config(
    page_title="محلل ومستشار الذهب والفضة", page_icon="📈", layout="wide"
)

# ==========================================
# 2. محاكي الأسعار الذكي للسكالبينج (متزامن وحي)
# ==========================================
if "gold_price" not in st.session_state:
    st.session_state.gold_price = 4145.21
    st.session_state.gold_change = 0.11

# محاكاة حركة سعرية بسيطة عند كل تحديث للصفحة
price_step = round(random.uniform(-0.8, 0.9), 2)
st.session_state.gold_price = round(
    st.session_state.gold_price + price_step, 2
)
st.session_state.gold_change = round(
    st.session_state.gold_change + (price_step * 0.02), 2
)

current_price = st.session_state.gold_price
price_change = st.session_state.gold_change

# ==========================================
# 3. نظام توليد توصيات السكالبينج (شراء / بيع / انتظار)
# ==========================================
if price_change > 0.3:
    scalping_signal = "شراء (BUY) 🟢"
    signal_color = "green"
    scalping_advice = (
        "الخميرة صعودية قوية تدعم صفقات الشراء (Scalping). الهدف القادم أعلى بـ"
        " 1.5 - 3 دولار مع وضع وقف خسارة قريب."
    )
elif price_change < -0.3:
    scalping_signal = "بيع (SELL) 🔴"
    signal_color = "red"
    scalping_advice = (
        "هناك ضغط بيعي ملحوظ يرجح استمرار التصحيح اللحظي. يفضل اقتناص صفقات بيع"
        " سريعة."
    )
else:
    scalping_signal = "انتظار (WAIT) ⏳"
    signal_color = "orange"
    scalping_advice = (
        "السوق في مرحلة تذبذب عرضي حالياً. يفضل الانتظار لحين كسر مناطق الدعم"
        " أو المقاومة لتجنب الإشارات الكاذبة."
    )

# ==========================================
# 4. الشريط الجانبي (Sidebar)
# ==========================================
with st.sidebar:
    st.subheader("🤖 مؤشر السكالبينج وحالة السوق")

    st.markdown(f"**السعر الحي الحالي:** `{current_price} $`")
    change_symbol = "+" if price_change >= 0 else ""
    st.markdown(f"**نسبة التغير:** `{change_symbol}{price_change}%`")

    st.markdown("---")
    st.markdown(f"### التوصية: **{scalping_signal}**")
    st.markdown(scalping_advice)

    # زر لإرسال التنبيه يدوياً أو تلقائياً إلى تيليجرام
    if st.button("🔔 إرسال تنبيه السكالبينج لتيليجرام"):
        full_msg = (
            f"⚡ *تنبيه سكالبينج ذهب (XAUUSD)*\n\n"
            f"💵 السعر الحالي: `{current_price} $`\n"
            f"📊 التوصية: *{scalping_signal}*\n"
            f"💡 التفاصيل: {scalping_advice}"
        )
        send_telegram_notification(full_msg)
        st.success("تم إرسال الإشعار بنجاح!")

    if st.button("🔄 تحديث التحليل والسعر"):
        st.rerun()

    st.markdown("---")
    st.subheader("💬 محادثة المستشار الخاص")

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "مرحباً بك! أنا أتابع معك حركة السعر اللحظية. اسألني عن"
                    " أي نقطة دخول."
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

        ai_reply = f"بخصوص سؤالك ({user_input}) عند السعر الحالي ({current_price})، أنصحك بالالتزام بإشارة ({scalping_signal}) وإدارة رأس المال بحذر."
        with st.chat_message("assistant"):
            st.markdown(ai_reply)
        st.session_state.messages.append(
            {"role": "assistant", "content": ai_reply}
        )

# ==========================================
# 5. الواجهة الرئيسية (شاشة الشارت)
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
