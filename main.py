import datetime
import os
import random
import uuid
import requests
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
    os.getenv("GROQ_API_KEY", ""),
)

client = None
if GROQ_API_KEY:
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=GROQ_API_KEY,
    )


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
        if client is None:
            return "⚠ لم يتم إعداد GROQ_API_KEY في Secrets/Environment."
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
# 6. Remote MT5 Bridge
# ==========================================
def normalize_bridge_url(url: str) -> str:
    """تنظيف رابط الـ Bridge وإزالة / في النهاية."""
    return (url or "").strip().rstrip("/")


def check_remote_bridge(base_url: str, token: str = ""):
    """فحص صحة Bridge API على الـ VPS."""
    base_url = normalize_bridge_url(base_url)
    if not base_url:
        return False, "رابط Bridge غير موجود."

    headers = {}
    if token:
        headers["X-Bridge-Token"] = token

    try:
        response = requests.get(
            f"{base_url}/health",
            headers=headers,
            timeout=8,
        )
        if response.ok:
            try:
                data = response.json()
                return True, data
            except ValueError:
                return True, response.text
        return False, f"HTTP {response.status_code}: {response.text[:300]}"
    except requests.RequestException as exc:
        return False, f"تعذر الاتصال: {exc}"


def send_remote_signal(
    base_url: str,
    token: str,
    symbol: str,
    side: str,
    volume: float,
    entry: float,
    sl: float,
    tp: float,
    signal_id: str,
):
    """
    إرسال إشارة إلى Remote MT5 Bridge.
    هذه الدالة لا تتصل بـ MT5 مباشرة؛ الـ Bridge/EA على الـ VPS هو الذي ينفذ الأمر.
    """
    base_url = normalize_bridge_url(base_url)

    if not base_url:
        return False, "أدخل Bridge API URL."
    if not token:
        return False, "أدخل Bridge Token."
    if side not in {"BUY", "SELL"}:
        return False, "نوع الصفقة يجب أن يكون BUY أو SELL."
    if volume <= 0:
        return False, "حجم الصفقة يجب أن يكون أكبر من صفر."
    if entry <= 0 or sl <= 0 or tp <= 0:
        return False, "Entry / SL / TP يجب أن تكون أرقاماً موجبة."

    # فحص هندسة SL/TP قبل الإرسال.
    if side == "BUY" and not (sl < entry < tp):
        return False, "في BUY يجب أن يكون SL < Entry < TP."
    if side == "SELL" and not (tp < entry < sl):
        return False, "في SELL يجب أن يكون TP < Entry < SL."

    payload = {
        "signal_id": signal_id,
        "symbol": symbol.strip(),
        "side": side,
        "volume": float(volume),
        "entry": float(entry),
        "sl": float(sl),
        "tp": float(tp),
    }

    try:
        response = requests.post(
            f"{base_url}/signal",
            json=payload,
            headers={"X-Bridge-Token": token},
            timeout=12,
        )
        try:
            result = response.json()
        except ValueError:
            result = response.text

        if response.ok:
            return True, result

        return False, f"HTTP {response.status_code}: {result}"
    except requests.RequestException as exc:
        return False, f"تعذر إرسال الإشارة: {exc}"


# ==========================================
# 7. الشريط الجانبي (Sidebar)
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

                if client is None:
                    ai_reply = "⚠ لم يتم إعداد GROQ_API_KEY في Secrets/Environment."
                else:
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
# Remote MT5 — إعدادات وإرسال الأوامر
# ==========================================
with st.sidebar:
    st.markdown("---")
    st.subheader("🌐 Remote MT5 على VPS")

    st.caption(
        "هذا الربط يرسل الإشارة إلى Bridge API على الـ VPS. "
        "تنفيذ BUY/SELL يتم بواسطة EA داخل MT5."
    )

    bridge_url = st.text_input(
        "Bridge API URL",
        value=os.getenv("MILA_BRIDGE_URL", ""),
        placeholder="https://your-vps-domain.com",
        help="رابط FastAPI Bridge الموجود على الـ VPS.",
    )

    bridge_token = st.text_input(
        "Bridge Token",
        value=os.getenv("MILA_BRIDGE_TOKEN", ""),
        type="password",
        help="لا تضع الـ Token داخل GitHub. استخدم Streamlit Secrets.",
    )

    remote_symbol = st.text_input(
        "رمز MT5 البعيد",
        value="XAUUSD",
        help="يجب أن يطابق اسم الرمز في MT5 على الـ VPS مثل XAUUSD أو XAUUSDm.",
    )

    remote_volume = st.number_input(
        "حجم الصفقة (Lot)",
        min_value=0.01,
        max_value=100.0,
        value=0.01,
        step=0.01,
    )

    remote_enabled = st.checkbox(
        "تفعيل Remote MT5",
        value=False,
        help="عند التفعيل تظهر أدوات إرسال الأوامر.",
    )

    if st.button("🔎 فحص اتصال الـ Bridge", use_container_width=True):
        ok, result = check_remote_bridge(bridge_url, bridge_token)
        if ok:
            st.success(f"Bridge متصل: {result}")
        else:
            st.error(result)

    if remote_enabled:
        st.markdown("### 📤 إرسال أمر يدوي")

        remote_side = st.selectbox(
            "نوع العملية",
            ["BUY", "SELL"],
            index=0,
        )

        remote_entry = st.number_input(
            "Entry",
            min_value=0.0,
            value=float(market["price"]),
            step=0.01,
            format="%.2f",
        )

        if remote_side == "BUY":
            default_sl = max(0.01, float(remote_entry) - 2.0)
            default_tp = float(remote_entry) + 3.0
        else:
            default_sl = float(remote_entry) + 2.0
            default_tp = max(0.01, float(remote_entry) - 3.0)

        remote_sl = st.number_input(
            "Stop Loss (SL)",
            min_value=0.0,
            value=float(round(default_sl, 2)),
            step=0.01,
            format="%.2f",
        )

        remote_tp = st.number_input(
            "Take Profit (TP)",
            min_value=0.0,
            value=float(round(default_tp, 2)),
            step=0.01,
            format="%.2f",
        )

        live_confirm = st.checkbox(
            "أؤكد أن هذا الأمر مخصص للتنفيذ الحقيقي",
            value=False,
            help="اتركه غير محدد للاختبار. لا يتم إرسال أمر تداول حتى تؤكد.",
        )

        send_button = st.button(
            "🚀 إرسال BUY/SELL إلى MT5 البعيد",
            type="primary",
            use_container_width=True,
            disabled=not live_confirm,
        )

        if send_button:
            signal_id = (
                f"manual-{remote_symbol.strip()}-"
                f"{remote_side}-{uuid.uuid4().hex[:12]}"
            )

            ok, result = send_remote_signal(
                base_url=bridge_url,
                token=bridge_token,
                symbol=remote_symbol,
                side=remote_side,
                volume=remote_volume,
                entry=remote_entry,
                sl=remote_sl,
                tp=remote_tp,
                signal_id=signal_id,
            )

            if ok:
                st.success(f"تم إرسال الإشارة إلى Bridge بنجاح. ID: {signal_id}")
                st.json(result)
            else:
                st.error(result)

        st.warning(
            "⚠️ تأكد أولاً أن الـ Bridge يعمل على الـ VPS وأن EA داخل MT5 "
            "مفعل ومسموح له بالاتصال. ابدأ بحساب Demo."
        )

# ==========================================
# 8. الواجهة الرئيسية (شاشة الشارت)
# ==========================================
st.title("📈 محطة تحليل الذهب والفضة & الشاشة الحية")

# حالة Remote MT5 في الواجهة الرئيسية
if remote_enabled:
    st.info(
        "🌐 Remote MT5 مفعّل — أوامر التداول تُرسل إلى Bridge API فقط، "
        "ثم يقوم EA الموجود داخل MT5 على الـ VPS بالتنفيذ."
    )

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
