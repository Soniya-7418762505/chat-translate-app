import os
import json
import html
import urllib.parse
from datetime import datetime
import streamlit as st

# Import translation libraries with graceful fallbacks
try:
    from deep_translator import GoogleTranslator, MyMemoryTranslator
    TRANSLATOR_LIB_AVAILABLE = True
except ImportError:
    TRANSLATOR_LIB_AVAILABLE = False

import requests

# ---------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="Chat Translate App",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# Custom Modern UI Styling (CSS)
# ---------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    /* Main Container Padding */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 950px;
    }

    /* App Header Card */
    .app-header {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 1.5rem 2rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 30px -10px rgba(99, 102, 241, 0.25);
    }
    .app-title {
        font-size: 2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #818cf8 0%, #c084fc 50%, #f472b6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .app-subtitle {
        color: #94a3b8;
        font-size: 0.95rem;
        font-weight: 400;
    }

    /* Chat bubble enhancements */
    .chat-tag {
        font-size: 0.75rem;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 6px;
        background: rgba(99, 102, 241, 0.15);
        color: #a5b4fc;
        margin-right: 6px;
        display: inline-block;
    }
    .provider-tag {
        font-size: 0.70rem;
        font-weight: 500;
        color: #64748b;
        margin-left: 8px;
    }

    /* Custom sidebar card */
    .sidebar-card {
        background: rgba(30, 41, 59, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 1rem;
    }

    /* Streamlit Button Tweaks */
    div.stButton > button:first-child {
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Supported Languages List
# ---------------------------------------------------------
LANGUAGES = {
    "English": {"code": "en", "flag": "🇺🇸", "native": "English"},
    "Tamil": {"code": "ta", "flag": "🇮🇳", "native": "தமிழ்"},
    "Hindi": {"code": "hi", "flag": "🇮🇳", "native": "हिन्दी"},
    "Malayalam": {"code": "ml", "flag": "🇮🇳", "native": "മലയാളം"},
    "Telugu": {"code": "te", "flag": "🇮🇳", "native": "తెలుగు"},
    "Spanish": {"code": "es", "flag": "🇪🇸", "native": "Español"},
    "French": {"code": "fr", "flag": "🇫🇷", "native": "Français"},
    "German": {"code": "de", "flag": "🇩🇪", "native": "Deutsch"},
    "Chinese": {"code": "zh", "flag": "🇨🇳", "native": "中文"},
    "Arabic": {"code": "ar", "flag": "🇸🇦", "native": "العربية"},
    "Japanese": {"code": "ja", "flag": "🇯🇵", "native": "日本語"},
    "Russian": {"code": "ru", "flag": "🇷🇺", "native": "Русский"},
    "Portuguese": {"code": "pt", "flag": "🇵🇹", "native": "Português"},
    "Italian": {"code": "it", "flag": "🇮🇹", "native": "Italiano"},
    "Korean": {"code": "ko", "flag": "🇰🇷", "native": "한국어"},
}

LANG_NAMES = list(LANGUAGES.keys())

# ---------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "source_lang_name" not in st.session_state:
    st.session_state.source_lang_name = "English"

if "target_lang_name" not in st.session_state:
    st.session_state.target_lang_name = "Tamil"

# ---------------------------------------------------------
# Translation Functions with Multi-Provider Fallback
# ---------------------------------------------------------
def translate_text(text: str, source_lang: str, target_lang: str):
    """
    Translates text with automatic multi-tier fallback:
    1. High-speed Google Translate Engine (Chrome Dict API)
    2. DeepTranslator GoogleTranslator (if available)
    3. MyMemory REST API (with extended timeout & user-agent)
    4. DeepTranslator MyMemoryTranslator
    5. Configured LibreTranslate instance (optional)
    """
    trimmed = text.strip()
    if not trimmed:
        return "", "None"

    # Direct return if source and target are identical
    src_code = LANGUAGES.get(source_lang, {}).get("code", "en")
    tgt_code = LANGUAGES.get(target_lang, {}).get("code", "ta")

    if src_code == tgt_code:
        return trimmed, "Direct (Identical Languages)"

    # 1. Primary: High-speed Google Translate Engine (Chrome extension client)
    try:
        encoded_query = urllib.parse.quote(trimmed)
        url = f"https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl={src_code}&tl={tgt_code}&q={encoded_query}"
        res = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            },
            timeout=8
        )
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list) and len(data) > 0:
                first = data[0]
                result_str = first if isinstance(first, str) else first[0]
                if result_str and isinstance(result_str, str):
                    return html.unescape(result_str.strip()), "Google Translate Engine"
    except Exception:
        pass

    # 2. Secondary: Google Translator via deep-translator
    if TRANSLATOR_LIB_AVAILABLE:
        try:
            translator = GoogleTranslator(source=src_code, target=tgt_code)
            result = translator.translate(trimmed)
            if result:
                return html.unescape(result.strip()), "Google Translator (Library)"
        except Exception:
            pass

    # 3. Tertiary: MyMemory REST API (with 12s timeout and standard headers)
    try:
        encoded_query = urllib.parse.quote(trimmed)
        url = f"https://api.mymemory.translated.net/get?q={encoded_query}&langpair={src_code}|{tgt_code}"
        res = requests.get(
            url,
            headers={"User-Agent": "ChatTranslateApp/1.0 (Mozilla/5.0)"},
            timeout=12
        )
        if res.status_code == 200:
            data = res.json()
            trans = data.get("responseData", {}).get("translatedText")
            if trans and isinstance(trans, str) and not trans.startswith("MYMEMORY WARNING"):
                return html.unescape(trans.strip()), "MyMemory Translation"
    except Exception:
        pass

    # 4. Quaternary: MyMemory via deep-translator
    if TRANSLATOR_LIB_AVAILABLE:
        try:
            translator = MyMemoryTranslator(source=src_code, target=tgt_code)
            result = translator.translate(trimmed)
            if result and not result.startswith("MYMEMORY WARNING"):
                return html.unescape(result.strip()), "MyMemory (Library)"
        except Exception:
            pass

    # 5. Configured LibreTranslate Endpoint (from st.secrets or os.environ if specified)
    libre_url = None
    try:
        libre_url = st.secrets.get("TRANSLATE_API_URL", None)
    except Exception:
        pass
    if not libre_url:
        libre_url = os.getenv("TRANSLATE_API_URL", None)

    if libre_url:
        api_key = None
        try:
            api_key = st.secrets.get("TRANSLATE_API_KEY", "")
        except Exception:
            pass
        if not api_key:
            api_key = os.getenv("TRANSLATE_API_KEY", "")

        try:
            payload = {"q": trimmed, "source": src_code, "target": tgt_code, "format": "text"}
            if api_key:
                payload["api_key"] = api_key
            res = requests.post(libre_url, json=payload, timeout=8)
            if res.status_code == 200 and "translatedText" in res.json():
                return html.unescape(res.json()["translatedText"]), "LibreTranslate API"
        except Exception:
            pass

    # Safe fallback if network/providers are unreachable
    return f"{trimmed} (Note: Translation provider unavailable)", "Fallback"

# ---------------------------------------------------------
# Sidebar Configuration
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Settings & Languages")

    # Mode Selector
    app_mode = st.radio(
        "Application Mode:",
        ["💬 Chat & Translate", "🤖 AI Assistant Chat"],
        index=0
    )

    st.markdown("---")

    # Source Language Select
    src_idx = LANG_NAMES.index(st.session_state.source_lang_name) if st.session_state.source_lang_name in LANG_NAMES else 0
    selected_source = st.selectbox(
        "Source Language:",
        LANG_NAMES,
        index=src_idx,
        format_func=lambda x: f"{LANGUAGES[x]['flag']} {x} ({LANGUAGES[x]['native']})"
    )
    st.session_state.source_lang_name = selected_source

    # Swap Languages Button
    if st.button("⇄ Swap Languages", use_container_width=True):
        temp = st.session_state.source_lang_name
        st.session_state.source_lang_name = st.session_state.target_lang_name
        st.session_state.target_lang_name = temp
        st.rerun()

    # Target Language Select
    tgt_idx = LANG_NAMES.index(st.session_state.target_lang_name) if st.session_state.target_lang_name in LANG_NAMES else 1
    selected_target = st.selectbox(
        "Target Language:",
        LANG_NAMES,
        index=tgt_idx,
        format_func=lambda x: f"{LANGUAGES[x]['flag']} {x} ({LANGUAGES[x]['native']})"
    )
    st.session_state.target_lang_name = selected_target

    st.markdown("---")
    st.markdown("#### ⚡ Quick Presets")
    presets_col1, presets_col2 = st.columns(2)
    with presets_col1:
        if st.button("EN ➔ Tamil", use_container_width=True):
            st.session_state.source_lang_name = "English"
            st.session_state.target_lang_name = "Tamil"
            st.rerun()
        if st.button("EN ➔ Telugu", use_container_width=True):
            st.session_state.source_lang_name = "English"
            st.session_state.target_lang_name = "Telugu"
            st.rerun()
    with presets_col2:
        if st.button("EN ➔ Hindi", use_container_width=True):
            st.session_state.source_lang_name = "English"
            st.session_state.target_lang_name = "Hindi"
            st.rerun()
        if st.button("EN ➔ Malayalam", use_container_width=True):
            st.session_state.source_lang_name = "English"
            st.session_state.target_lang_name = "Malayalam"
            st.rerun()

    st.markdown("---")

    # Chat Actions (Clear & Download)
    st.markdown("#### 🛠️ Chat Actions")
    if st.button("🧹 Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    # Export Transcript
    if st.session_state.messages:
        transcript_data = "\n\n".join([
            f"[{m.get('time', '')}] {m['role'].upper()} ({m.get('lang', '')}):\nOriginal: {m.get('original', m.get('content', ''))}\nTranslated: {m.get('content', '')}"
            for m in st.session_state.messages
        ])
        st.download_button(
            label="📥 Download Chat (.txt)",
            data=transcript_data,
            file_name=f"chat_translate_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            use_container_width=True
        )

    st.markdown("---")
    st.caption("🚀 **Chat App** • Streamlit Community Cloud Ready")

# ---------------------------------------------------------
# Main Header
# ---------------------------------------------------------
src_flag = LANGUAGES[st.session_state.source_lang_name]["flag"]
tgt_flag = LANGUAGES[st.session_state.target_lang_name]["flag"]

st.markdown(f"""
<div class="app-header">
    <div class="app-title">Chat Translate App</div>
    <div class="app-subtitle">
        Real-time multi-language chat translation &bull; Active Pair: <strong>{src_flag} {st.session_state.source_lang_name} ➔ {tgt_flag} {st.session_state.target_lang_name}</strong>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Display Chat History
# ---------------------------------------------------------
if not st.session_state.messages:
    st.info(f"👋 Welcome! Type your message in the box below to chat and translate from **{st.session_state.source_lang_name}** to **{st.session_state.target_lang_name}**.")
else:
    for msg in st.session_state.messages:
        role = msg["role"]
        content = msg["content"]
        time_str = msg.get("time", "")
        lang_str = msg.get("lang", "")
        provider = msg.get("provider", "")
        original = msg.get("original", "")

        if role == "user":
            with st.chat_message("user", avatar="👤"):
                st.markdown(f"<span class='chat-tag'>{lang_str}</span> <small style='color:#64748b;'>{time_str}</small>", unsafe_allow_html=True)
                st.write(content)
        else:
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(f"<span class='chat-tag'>{lang_str}</span> <small style='color:#64748b;'>{time_str}</small> <span class='provider-tag'>⚡ {provider}</span>", unsafe_allow_html=True)
                st.markdown(f"**{content}**")
                if original and original != content:
                    with st.expander("Show Original Text"):
                        st.caption(original)

# ---------------------------------------------------------
# Chat Input & Message Handler
# ---------------------------------------------------------
user_input = st.chat_input(f"Type message in {st.session_state.source_lang_name}...")

if user_input:
    current_time = datetime.now().strftime("%I:%M %p")
    source_name = st.session_state.source_lang_name
    target_name = st.session_state.target_lang_name

    # 1. Append User Message
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "lang": f"{LANGUAGES[source_name]['flag']} {source_name}",
        "time": current_time
    })

    # Render User Message immediately
    with st.chat_message("user", avatar="👤"):
        st.markdown(f"<span class='chat-tag'>{LANGUAGES[source_name]['flag']} {source_name}</span> <small style='color:#64748b;'>{current_time}</small>", unsafe_allow_html=True)
        st.write(user_input)

    # 2. Generate Translation / Response
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner(f"Translating to {target_name}..."):
            translated_result, used_provider = translate_text(user_input, source_name, target_name)

            st.markdown(f"<span class='chat-tag'>{LANGUAGES[target_name]['flag']} {target_name}</span> <small style='color:#64748b;'>{current_time}</small> <span class='provider-tag'>⚡ {used_provider}</span>", unsafe_allow_html=True)
            st.markdown(f"**{translated_result}**")

            # Append Assistant Message
            st.session_state.messages.append({
                "role": "assistant",
                "content": translated_result,
                "original": user_input,
                "lang": f"{LANGUAGES[target_name]['flag']} {target_name}",
                "provider": used_provider,
                "time": current_time
            })

    # Re-run to synchronize chat state
    st.rerun()
