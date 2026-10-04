import datetime
import random
import requests
import streamlit.components.v1 as components
import streamlit as st

# ==========================================
# 1. إعدادات تيليجرام للإشعارات الفورية
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
# 2. إعدادات الصفحة
# ==========================================
st.set_page_config(
    page_title="محلل ومستشار الذهب والفضة", page_icon="📈", layout="wide"
)

# ==========================================
# 3. إدارة حالة الأسعار والسكالبينج عبر زر التحديث فقط
# ==========================================
if "gold_price" not in st.session_state:
    st.session_state.gold_price = 4144.95
    st.session_state.gold_change = 0.11

current_price = st.session_state.gold_price
price_change = st.session_state.gold_change

# ==========================================
# 4. نظام توليد توصيات السكالبينج (شراء / بيع / انتظار)
# ==========================================
if price_change > 0.2:
    scalping_signal = "شراء (BUY) 🟢"
    scalping_advice = (
        "زخم صعودي لحظي يدعم صفقات الشراء السريعة (Scalping). الهدف القادم أعلى"
        " بـ 1 - 2 دولار مع وضع وقف خسارة قريب."
    )
elif price_change < -0.2:
    scalping_signal = "بيع (SELL) 🔴"
    scalping_advice = (
        "ضغط بيعي قصير المدى يرجح استمرار التراجع اللحظي. يفضل اقتناص صفقات بيع"
        " سريعة."
    )
else:
    scalping_signal = "انتظار (WAIT) ⏳"
    scalping_advice = (
        "حركة عرضية متذبذبة حالياً. يفضل الانتظار لحين اتضاح الاتجاه أو كسر"
        " مستويات الدعم والمقاومة."
    )

# ==========================================
# 5. الشريط الجانبي (Sidebar)
# ==========================================
with st.sidebar:
    st.subheader("⚡ مؤشر السكالبينج (تحديث يدوي)")

    st.markdown(f"**السعر الحالي:** `{current_price} $`")
    change_symbol = "+" if price_change >= 0 else ""
    st.markdown(f"**نسبة التغير:** `{change_symbol}{price_change}%`")

    st.markdown("---")
    st.markdown(f"### التوصية: **{scalping_signal}**")
    st.markdown(scalping_advice)

    # زر التحديث اليدوي المباشر للتحليل والسعر
    if st.button("🔄 تحديث التحليل والسعر"):
        price_step = round(random.uniform(-0.4, 0.45), 2)
        st.session_state.gold_price = round(
            st.session_state.gold_price + price_step, 2
        )
        st.session_state.gold_change = round(
            st.session_state.gold_change + (price_step * 0.01), 2
        )
        st.rerun()

    # زر إرسال تنبيه يدوي لتيليجرام
    if st.button("🔔 إرسال تنبيه السكالبينج لتيليجرام"):
        full_msg = (
            f"⚡ *تنبيه سكالبينج ذهب (XAUUSD)*\n\n"
            f"💵 السعر الحالي: `{current_price} $`\n"
            f"📊 التوصية: *{scalping_signal}*\n"
            f"💡 التفاصيل: {scalping_advice}"
        )
        send_telegram_notification(full_msg)
        st.success("تم إرسال الإشعار بنجاح!")

    st.markdown("---")
    st.subheader("💬 محادثة المستشار الخاص")

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "مرحباً بك! أنا أتابع معك حركة السعر. اضغط على زر التحديث"
                    " متى ما أردت تحديث التحليل."
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

        ai_reply = f"بخصوص سؤالك ({user_input}) عند السعر الحالي ({current_price})، أنصحك بالالتزام بإشارة ({scalping_signal}) وإدارة رأس المال بدقة."
        with st.chat_message("assistant"):
            st.markdown(ai_reply)
        st.session_state.messages.append(
            {"role": "assistant", "content": ai_reply}
        )

# ==========================================
# 6. الواجهة الرئيسية (شاشة الشارت)
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
