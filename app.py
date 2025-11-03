import streamlit as st
import os
import base64
import json
import hmac
import hashlib
import time as _rt
import uuid
import threading
from dotenv import load_dotenv
from src.chatapp.chat import get_chat_response, clear_memory, conversation_chain, get_memory_messages
from src.chatapp.logger import logging
import traceback

# Load environment variables
load_dotenv()

# Read config helper: use Streamlit Secrets first (Cloud), fallback to .env (local)
def get_cfg(key: str, default: str | None = None):
    try:
        # flat key in secrets (preferred on Cloud)
        if key in st.secrets:
            return st.secrets.get(key, default)
        # allow nested tables, e.g., st.secrets["auth"][key]
        for k, v in getattr(st, "secrets", {}).items():
            try:
                if isinstance(v, dict) and key in v:
                    return v.get(key, default)
            except Exception:
                pass
    except Exception:
        pass
    return os.getenv(key, default)

# ---------------- Security: Simple Auth Gate (limit to 3 users) ----------------
# Expected in Streamlit Secrets (Deploy → App settings → Secrets):
# [auth]
# users = ["user1", "user2", "user3"]
# passwords = {"user1": "pass1", "user2": "pass2", "user3": "pass3"}
# session_minutes = 60
# rate_limit_per_min = 20

auth_cfg = {
    "users": [],
    "passwords": {},
    "shared_password": None,
    "session_minutes": 60,
}
try:
    # Prefer nested [auth] table
    if "auth" in st.secrets:
        sec = st.secrets["auth"]
        auth_cfg["users"] = list(sec.get("users", []))
        auth_cfg["passwords"] = dict(sec.get("passwords", {}))
        auth_cfg["shared_password"] = sec.get("shared_password")
        auth_cfg["session_minutes"] = int(sec.get("session_minutes", 60))
    else:
        # Also support flat secrets keys
        flat = st.secrets
        if "shared_password" in flat:
            auth_cfg["shared_password"] = flat.get("shared_password")
        if "session_minutes" in flat:
            auth_cfg["session_minutes"] = int(flat.get("session_minutes", 60))
except Exception:
    pass

# Fallback to environment variables if secrets missing
if not auth_cfg.get("shared_password"):
    env_sp = os.getenv("SHARED_PASSWORD")
    if env_sp:
        auth_cfg["shared_password"] = env_sp

# (moved earlier) Concurrency helpers defined above

# Enforce max 3 users
if len(auth_cfg["users"]) > 3:
    auth_cfg["users"] = auth_cfg["users"][:3]

# ---------------- Concurrency limit: at most 2 active sessions ----------------
_ACTIVE_SESSIONS_LOCK = threading.Lock()
_ACTIVE_SESSIONS = {}

# Restore session from URL token if signed with shared password (prevents spoofing)
try:
    import time as _qt
    try:
        _params = st.query_params
    except Exception:
        _params = st.experimental_get_query_params()
    _tok = None
    _sig = None
    if isinstance(_params, dict):
        def _first(v):
            return v if isinstance(v, str) else (v[0] if isinstance(v, list) and v else None)
        if "auth" in _params:
            _tok = _first(_params["auth"])
        if "sig" in _params:
            _sig = _first(_params["sig"])
    if _tok and _sig and auth_cfg.get("shared_password"):
        expected = hmac.new(
            key=str(auth_cfg["shared_password"]).encode("utf-8"),
            msg=str(_tok).encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()
        # Token must be signed AND already registered as an active session
        if hmac.compare_digest(expected, _sig) and _tok in _ACTIVE_SESSIONS:
            st.session_state["session_id"] = _tok
            st.session_state["auth_ok"] = True
            st.session_state["user"] = st.session_state.get("user", "shared_user")
            st.session_state["login_ts"] = _qt.time()
            # Register session in active sessions
            with _ACTIVE_SESSIONS_LOCK:
                _ACTIVE_SESSIONS[_tok] = _qt.time()
except Exception:
    pass

def _prune_sessions():
    now = _rt.time()
    ttl = max(5 * 60, auth_cfg.get("session_minutes", 60) * 60)
    stale = [sid for sid, ts in _ACTIVE_SESSIONS.items() if (now - ts) > ttl]
    for sid in stale:
        _ACTIVE_SESSIONS.pop(sid, None)

def _ensure_session_id():
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = str(uuid.uuid4())
    return st.session_state["session_id"]

def _touch_session():
    sid = _ensure_session_id()
    with _ACTIVE_SESSIONS_LOCK:
        _prune_sessions()
        _ACTIVE_SESSIONS[sid] = _rt.time()

def _remove_session():
    sid = st.session_state.get("session_id")
    if not sid:
        return
    with _ACTIVE_SESSIONS_LOCK:
        _ACTIVE_SESSIONS.pop(sid, None)

def _can_login_with_concurrency_limit(max_sessions: int = 2) -> bool:
    # If this session already registered, allow
    sid = st.session_state.get("session_id")
    with _ACTIVE_SESSIONS_LOCK:
        _prune_sessions()
        if sid and sid in _ACTIVE_SESSIONS:
            return True
        return len(_ACTIVE_SESSIONS) < max_sessions

def is_authenticated() -> bool:
    if st.session_state.get("auth_ok"):
        # Session expiry
        login_ts = st.session_state.get("login_ts")
        if login_ts:
            import time
            if (time.time() - login_ts) > auth_cfg["session_minutes"] * 60:
                # Clear session on expiry
                try:
                    _remove_session()
                except Exception:
                    pass
                st.session_state.clear()
                st.warning("Session expired. Please login again.")
                return False
        # Ensure session is registered in active sessions
        sid = st.session_state.get("session_id")
        if sid:
            try:
                with _ACTIVE_SESSIONS_LOCK:
                    if sid not in _ACTIVE_SESSIONS:
                        _ACTIVE_SESSIONS[sid] = _rt.time()
            except Exception:
                pass
        return True
    return False

def render_login():
    st.markdown("<div style='height: 1rem'></div>", unsafe_allow_html=True)
    st.subheader("🔐 Secure Access")
    if not auth_cfg.get("shared_password"):
        st.error("Shared password not configured. Set [auth].shared_password in Secrets.")
        return

    with st.form("login_form_shared", clear_on_submit=False):
        password = st.text_input("Password", type="password")
        col1, col2 = st.columns([1,1])
        with col1:
            submitted = st.form_submit_button("Login")
        with col2:
            reset_clicked = st.form_submit_button("Reset sessions")

    if reset_clicked:
        try:
            with _ACTIVE_SESSIONS_LOCK:
                _ACTIVE_SESSIONS.clear()
            st.success("Active sessions reset. Try logging in now.")
        except Exception:
            st.warning("Could not reset sessions.")

    if submitted:
        # Concurrency check (max 2)
        if password == auth_cfg["shared_password"] and _can_login_with_concurrency_limit():
            import time
            st.session_state["auth_ok"] = True
            st.session_state["user"] = "shared_user"
            st.session_state["login_ts"] = time.time()
            _touch_session()  # Register session immediately
            # Persist signed token in URL (auth=token, sig=hmac) to survive refresh
            try:
                _tok = st.session_state.get("session_id") or ""
                _sig = hmac.new(
                    key=str(auth_cfg["shared_password"]).encode("utf-8"),
                    msg=str(_tok).encode("utf-8"),
                    digestmod=hashlib.sha256,
                ).hexdigest()
                try:
                    st.query_params = {"auth": _tok, "sig": _sig}
                except Exception:
                    st.experimental_set_query_params(auth=_tok, sig=_sig)
            except Exception:
                pass
            st.success("Login successful")
            st.rerun()
        else:
            st.error("Invalid password or maximum concurrent users reached")

if not is_authenticated():
    render_login()
    st.stop()

# Logout control in sidebar
with st.sidebar:
    if st.button("🚪 Logout", use_container_width=True):
        try:
            _remove_session()
        finally:
            # Clear auth token from URL so refresh doesn't auto-login
            try:
                try:
                    st.query_params = {}
                except Exception:
                    st.experimental_set_query_params()
            except Exception:
                pass
            st.session_state.clear()
        st.rerun()

# Mark activity for concurrency tracking when authenticated
try:
    if is_authenticated():
        _touch_session()
except Exception:
    pass

# Rate limiting removed per user request



# Check if environment variables are set
def check_env_variables():
    """Check if required environment variables are set"""
    api_key = get_cfg("AZURE_OPENAI_API_KEY")
    endpoint = get_cfg("AZURE_OPENAI_ENDPOINT")
    api_version = get_cfg("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
    
    missing = []
    if not api_key or api_key == "your_azure_openai_api_key_here":
        missing.append("AZURE_OPENAI_API_KEY")
    if not endpoint or endpoint == "your_azure_openai_endpoint_here":
        missing.append("AZURE_OPENAI_ENDPOINT")
    
    return missing, api_key, endpoint, api_version

# Page Configuration
st.set_page_config(
    page_title="QA Assistant - Defect Report Generator",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for beautiful modern ChatGPT-like styling
st.markdown("""
<style>
    /* Hide streamlit branding completely */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    /* Keep header visible so the sidebar toggle is accessible */
    .stDeployButton {display: none;}
    
    /* Global body styling */
    .main {
        background: #f5f7fa;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    }
    
    /* Main container styling */
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 950px;
        background: white;
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        margin-top: 2rem;
        margin-bottom: 2rem;
    }
    
    /* Title styling - Modern and beautiful */
    h1 {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 1rem;
        text-align: center;
        letter-spacing: -0.5px;
    }
    
    /* Chat message styling - Beautiful cards */
    .stChatMessage {
        padding: 1.5rem;
        border-radius: 18px;
        margin-bottom: 1.5rem;
        position: relative;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        border: 1px solid rgba(255,255,255,0.8);
        backdrop-filter: blur(10px);
    }
    
    .stChatMessage:hover {
        box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        transform: translateY(-2px);
    }
    
    /* User message styling */
    [data-testid="stChatMessage"]:has([data-testid="stChatAvatar"]) {
        background: linear-gradient(135deg, #f6f8fb 0%, #e9ecef 100%);
        border-left: 4px solid #667eea;
    }
    
    /* Assistant message styling */
    [data-testid="stChatMessage"]:not(:has([data-testid="stChatAvatar"])) {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        border-left: 4px solid #764ba2;
    }
    
    /* Sidebar styling - Modern glass effect */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
        border-radius: 0 20px 20px 0;
    }
    
    section[data-testid="stSidebar"] > div {
        background-color: rgba(255,255,255,0.05);
        backdrop-filter: blur(10px);
    }
    
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: white !important;
    }
    
    section[data-testid="stSidebar"] .stMarkdown {
        color: rgba(255,255,255,0.9) !important;
    }
    
    /* Sidebar metrics */
    section[data-testid="stSidebar"] [data-testid="stMetricValue"] {
        color: white;
    }
    
    section[data-testid="stSidebar"] [data-testid="stMetricLabel"] {
        color: rgba(255,255,255,0.8);
    }
    
    /* Input styling - Beautiful modern input */
    .stChatInput > div > div > textarea {
        border-radius: 25px !important;
        border: 2px solid #e5e7eb !important;
        padding: 1rem 1.5rem !important;
        font-size: 1rem !important;
        background: white !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
        transition: all 0.3s ease !important;
    }
    
    .stChatInput > div > div > textarea:focus {
        border-color: #667eea !important;
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.3) !important;
        outline: none !important;
    }
    
    /* Button styling - Modern gradient buttons */
    .stButton > button {
        border-radius: 12px !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
        border: none !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) scale(1.02) !important;
        box-shadow: 0 8px 20px rgba(0,0,0,0.15) !important;
    }
    
    /* Primary button gradient */
    button[kind="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
    }
    
    button[kind="secondary"] {
        background: rgba(255,255,255,0.2) !important;
        color: white !important;
        backdrop-filter: blur(10px) !important;
    }
    
    /* Spinner styling */
    .stSpinner > div {
        border-color: #667eea;
        border-top-color: transparent;
    }
    
    /* Info boxes in sidebar */
    section[data-testid="stSidebar"] .stInfo {
        background: rgba(255,255,255,0.15) !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
        border-radius: 12px !important;
        backdrop-filter: blur(10px) !important;
    }
    
    /* Smooth transitions */
    * {
        transition: background-color 0.3s ease, color 0.3s ease, transform 0.3s ease;
    }
    
    /* Custom scrollbar - Beautiful */
    ::-webkit-scrollbar {
        width: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f3f5;
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
    
    /* Chat input container - ensure it stays at bottom always */
    .stChatInputContainer {
        background: white !important;
        padding: 1rem !important;
        border-radius: 20px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
        margin-top: 2rem !important;
        position: fixed !important;
        bottom: 1rem !important;
        left: 0 !important;
        right: 0 !important;
        z-index: 999 !important;
        max-width: 950px !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }
    
    /* Ensure main content has padding at bottom to not overlap with fixed input */
    .main .block-container {
        padding-bottom: 8rem !important;
    }
    
    /* Ensure chat input appears after all content */
    [data-testid="stChatInput"] {
        margin-top: auto !important;
        width: 100% !important;
    }
    
    /* Auto-scroll to bottom when new messages arrive */
    .element-container:has([data-testid="stChatInput"]) {
        position: fixed !important;
        bottom: 1rem !important;
        width: 100% !important;
        max-width: 950px !important;
        left: 50% !important;
        transform: translateX(-50%) !important;
        padding: 0 1rem !important;
    }
    
    /* Chat input field */
    .stChatInput > div > div > input {
        border-radius: 25px !important;
        padding: 0.75rem 1.25rem !important;
        font-size: 1rem !important;
        border: 2px solid #e5e7eb !important;
        transition: all 0.3s ease !important;
    }
    
    .stChatInput > div > div > input:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1) !important;
    }
    
    /* Success message styling */
    .stSuccess {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 12px;
        padding: 0.75rem 1rem;
    }
    
    /* Error message styling */
    .stError {
        border-radius: 12px;
        padding: 1rem;
    }
    
    /* Metric cards in sidebar */
    section[data-testid="stSidebar"] [data-testid="stMetricContainer"] {
        background: rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 1rem;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.2);
    }
    
    /* Copy button styling */
    button[kind="secondary"]:has-text("📋") {
        background: rgba(255,255,255,0.3) !important;
        font-size: 1.2rem !important;
    }
    
    /* Remove all horizontal rules */
    hr {
        display: none;
    }
    
    /* Avatar styling */
    [data-testid="stChatAvatar"] {
        border-radius: 50%;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Message text styling */
    .stMarkdown {
        line-height: 1.7;
        color: #1f2937;
    }
    
    /* Better spacing between messages */
    [data-testid="stChatMessage"] {
        margin-bottom: 1rem !important;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        margin-bottom: 1.5rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 12px 12px 0 0;
        padding: 0.75rem 1.5rem;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(102, 126, 234, 0.05);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
    }
    
    /* Sidebar subheader */
    section[data-testid="stSidebar"] h3 {
        font-size: 1.1rem;
        font-weight: 600;
        margin-top: 1.5rem;
        margin-bottom: 0.75rem;
    }
</style>

<script>
    function scrollToBottom() {
        setTimeout(function() {
            window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
        }, 100);
    }
    
    // Scroll to bottom on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', scrollToBottom);
    } else {
        scrollToBottom();
    }
    
    // Scroll to bottom when new messages are added
    const observer = new MutationObserver(function(mutations) {
        let shouldScroll = false;
        for (let mutation of mutations) {
            if (mutation.addedNodes.length > 0) {
                shouldScroll = true;
                break;
            }
        }
        if (shouldScroll) {
            scrollToBottom();
        }
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
</script>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "chat_initialized" not in st.session_state:
    st.session_state.chat_initialized = True

# Check environment variables
missing_vars, api_key, endpoint, api_version = check_env_variables()

# Title and Header - Centered and beautiful
st.markdown("<div style='text-align: center; padding: 1rem 0;'>", unsafe_allow_html=True)
st.title("💬 AI Chat Assistant")
st.markdown("</div>", unsafe_allow_html=True)

# Create tabs for QA Assistant and Normal Chat
qa_tab, normal_tab = st.tabs(["🔍 QA Assistant", "💬 Normal Chat"])

# Show warning if environment variables are missing
if missing_vars:
    st.error(f"""
    ⚠️ **Configuration Required**
    
    Missing environment variables: {', '.join(missing_vars)}
    
    Please configure your `.env` file with the required settings.
    See `env.example` file for reference.
    """)
    st.stop()

# Initialize chat mode in session state
if "chat_mode" not in st.session_state:
    st.session_state.chat_mode = "qa"
if "qa_messages" not in st.session_state:
    st.session_state.qa_messages = []
if "normal_messages" not in st.session_state:
    st.session_state.normal_messages = []

# Sidebar with beautiful design
with st.sidebar:
    st.markdown("<div style='text-align: center; padding: 1rem 0; margin-bottom: 1rem;'>", unsafe_allow_html=True)
    st.markdown("<h2 style='color: #667eea; font-size: 1.5rem; margin: 0;'>⚙️ Settings</h2>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<hr style='margin: 1.5rem 0; border: none; border-top: 1px solid rgba(102, 126, 234, 0.2);'>", unsafe_allow_html=True)
    
    # Clear chat button - Beautiful gradient
    if st.button("🗑️ Clear Chat History", use_container_width=True, type="secondary"):
        current_mode = st.session_state.chat_mode
        clear_memory(current_mode)
        if current_mode == "qa":
            st.session_state.qa_messages = []
        else:
            st.session_state.normal_messages = []
        st.success("✨ Chat cleared successfully!")
        st.rerun()
    
    st.markdown("<hr style='margin: 1.5rem 0; border: none; border-top: 1px solid rgba(102, 126, 234, 0.2);'>", unsafe_allow_html=True)
    
    # Memory status - Beautiful card
    st.markdown("<div style='background: rgba(102, 126, 234, 0.08); padding: 1rem; border-radius: 12px; margin: 1rem 0; border: 1px solid rgba(102, 126, 234, 0.2);'>", unsafe_allow_html=True)
    st.markdown("<h3 style='color: #667eea; font-size: 1.1rem; margin-bottom: 0.5rem;'>📊 Memory Status</h3>", unsafe_allow_html=True)
    try:
        current_mode = st.session_state.chat_mode
        memory_messages = get_memory_messages(current_mode)
        st.markdown(f"<div style='font-size: 1.5rem; font-weight: 700; color: #667eea; margin: 0.5rem 0;'>{len(memory_messages)}</div>", unsafe_allow_html=True)
        st.markdown("<div style='color: #666; font-size: 0.9rem;'>messages remembered</div>", unsafe_allow_html=True)
    except:
        st.markdown("<div style='color: #666; font-size: 0.9rem;'>Memory system active</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    

# QA Assistant Tab
with qa_tab:
    st.session_state.chat_mode = "qa"
    current_messages = st.session_state.qa_messages
    
    # Welcome message - only show if no messages (reduced padding)
    if len(current_messages) == 0:
        st.markdown("<div class='welcome-card' style='text-align: center; padding: 1rem; background: #f8f9fa; border-radius: 16px; margin: 1rem 0; border: 1px solid #e9ecef;'>", unsafe_allow_html=True)
        st.markdown("""
        <div style="margin-bottom: 0.5rem;">
            <h2 style="color: #667eea; font-size: 1.5rem; margin-bottom: 0.25rem;">🔍 QA Assistant</h2>
            <p style="color: #666; font-size: 1rem; margin: 0;">Transform bug descriptions into professional defect reports</p>
        </div>
        <div style="margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid rgba(102, 126, 234, 0.2);">
            <p style="color: #888; font-size: 0.9rem; line-height: 1.5; margin: 0;">
                Simply describe your bug or issue below, and I'll create a comprehensive defect report with all the necessary details for your QA team.
            </p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Display chat history
    for idx, message in enumerate(current_messages):
        with st.chat_message(message["role"]):
            # Display message content
            st.markdown(message["content"])
        
        # Copy icon - Direct copy on click
        col1, col2 = st.columns([9.5, 0.5])
        with col1:
            st.empty()
        with col2:
            # Use Streamlit components for better JavaScript execution
            # Safety check: ensure content is a string
            content_str = str(message["content"]) if message.get("content") is not None else ""
            message_content = content_str.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$").replace("\n", "\\n").replace("\r", "\\r")
            
            st.components.v1.html(f"""
            <div style="text-align: right;">
                <button id="copyBtn_{idx}" onclick="handleCopy_{idx}()" 
                        style="background: transparent; border: none; cursor: pointer; font-size: 1.2rem; padding: 0.5rem; opacity: 0.7; transition: all 0.2s; border-radius: 6px;"
                        onmouseover="this.style.opacity='1'; this.style.backgroundColor='rgba(0,0,0,0.05)'"
                        onmouseout="this.style.opacity='0.7'; this.style.backgroundColor='transparent'"
                        title="Copy message">
                    📋
                </button>
                <script>
                    function handleCopy_{idx}() {{
                        const text = `{message_content}`;
                        const btn = document.getElementById('copyBtn_{idx}');
                        
                        // Try modern Clipboard API
                        if (navigator.clipboard && window.isSecureContext) {{
                            navigator.clipboard.writeText(text).then(() => {{
                                btn.innerHTML = '✅';
                                btn.style.color = '#10b981';
                                setTimeout(() => {{
                                    btn.innerHTML = '📋';
                                    btn.style.color = '';
                                }}, 1500);
                            }}).catch(() => {{
                                fallbackCopy_{idx}(text, btn);
                            }});
                        }} else {{
                            fallbackCopy_{idx}(text, btn);
                        }}
                    }}
                    
                    function fallbackCopy_{idx}(text, btn) {{
                        const textarea = document.createElement('textarea');
                        textarea.value = text;
                        textarea.style.position = 'fixed';
                        textarea.style.top = '-9999px';
                        textarea.style.left = '-9999px';
                        document.body.appendChild(textarea);
                        textarea.focus();
                        textarea.select();
                        try {{
                            const success = document.execCommand('copy');
                            document.body.removeChild(textarea);
                            if (success) {{
                                btn.innerHTML = '✅';
                                btn.style.color = '#10b981';
                                setTimeout(() => {{
                                    btn.innerHTML = '📋';
                                    btn.style.color = '';
                                }}, 1500);
                            }}
                        }} catch (err) {{
                            document.body.removeChild(textarea);
                            alert('Copy failed. Please select the text manually.');
                        }}
                    }}
                </script>
            </div>
            """, height=50)

    # Add spacer to push chat input to bottom
    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
    
    # Chat input for QA mode - placed after all messages
    if prompt := st.chat_input("💬 Describe your bug or issue to generate a defect report..."):
        # Add user message to chat history
        st.session_state.qa_messages.append({"role": "user", "content": prompt})
        
        # Display user message immediately
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get AI response with memory
        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking..."):
                try:
                    # Get response from chat chain (uses conversation memory)
                    response = get_chat_response(prompt, mode="qa")
                
                    # Display AI response
                    st.markdown(response)
                    
                    # Copy icon - Direct copy on click
                    col1, col2 = st.columns([9.5, 0.5])
                    with col1:
                        st.empty()
                    with col2:
                        msg_num = len(st.session_state.qa_messages)
                        response_escaped = response.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$").replace("\n", "\\n").replace("\r", "\\r")
                    
                    st.components.v1.html(f"""
                    <div style="text-align: right;">
                        <button id="copyAssistantBtn_qa_{msg_num}" onclick="handleCopyAssistantQA_{msg_num}()" 
                                style="background: transparent; border: none; cursor: pointer; font-size: 1.2rem; padding: 0.5rem; opacity: 0.7; transition: all 0.2s; border-radius: 6px;"
                                onmouseover="this.style.opacity='1'; this.style.backgroundColor='rgba(0,0,0,0.05)'"
                                onmouseout="this.style.opacity='0.7'; this.style.backgroundColor='transparent'"
                                title="Copy message">
                            📋
                        </button>
                        <script>
                            function handleCopyAssistant_{msg_num}() {{
                                const text = `{response_escaped}`;
                                const btn = document.getElementById('copyAssistantBtn_{msg_num}');
                                if (navigator.clipboard && window.isSecureContext) {{
                                    navigator.clipboard.writeText(text).then(() => {{
                                        btn.innerHTML = '✅';
                                        btn.style.color = '#10b981';
                                        setTimeout(() => {{ btn.innerHTML = '📋'; btn.style.color = ''; }}, 1500);
                                    }}).catch(() => {{ fallbackCopyAssistant_{msg_num}(text, btn); }});
                                }} else {{
                                    fallbackCopyAssistant_{msg_num}(text, btn);
                                }}
                            }}
                            function fallbackCopyAssistant_{msg_num}(text, btn) {{
                                const textarea = document.createElement('textarea');
                                textarea.value = text;
                                textarea.style.position = 'fixed';
                                textarea.style.top = '-9999px';
                                document.body.appendChild(textarea);
                                textarea.select();
                                document.execCommand('copy');
                                document.body.removeChild(textarea);
                                btn.innerHTML = '✅';
                                btn.style.color = '#10b981';
                                setTimeout(() => {{ btn.innerHTML = '📋'; btn.style.color = ''; }}, 1500);
                            }}
                        </script>
                    </div>
                    """, height=50)
                    
                    # Add assistant response to chat history
                    st.session_state.qa_messages.append({"role": "assistant", "content": response})
                    
                except Exception as e:
                    error_msg = f"❌ Sorry, I encountered an error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.qa_messages.append({"role": "assistant", "content": error_msg})
                    logging.error(f"Chat error: {str(e)}")
                    logging.error(traceback.format_exc())
                    st.exception(e)

# Normal Chat Tab
with normal_tab:
    st.session_state.chat_mode = "normal"
    current_messages = st.session_state.normal_messages
    
    # Welcome message - only show if no messages (reduced padding)
    if len(current_messages) == 0:
        st.markdown("<div class='welcome-card' style='text-align: center; padding: 1rem; background: #f8f9fa; border-radius: 16px; margin: 1rem 0; border: 1px solid #e9ecef;'>", unsafe_allow_html=True)
        st.markdown("""
        <div style="margin-bottom: 0.5rem;">
            <h2 style="color: #667eea; font-size: 1.5rem; margin-bottom: 0.25rem;">💬 Normal Chat</h2>
            <p style="color: #666; font-size: 1rem; margin: 0;">Have a conversation with your AI assistant</p>
        </div>
        <div style="margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid rgba(102, 126, 234, 0.2);">
            <p style="color: #888; font-size: 0.9rem; line-height: 1.5; margin: 0;">
                Ask me anything, and I'll do my best to help you with your questions, conversations, and tasks. I remember our conversation context.
            </p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Display chat history
    for idx, message in enumerate(current_messages):
        with st.chat_message(message["role"]):
            # Display message content
            st.markdown(message["content"])
            
            # Copy icon - Direct copy on click
            col1, col2 = st.columns([9.5, 0.5])
            with col1:
                st.empty()
            with col2:
                # Use Streamlit components for better JavaScript execution
                # Safety check: ensure content is a string
                content_str = str(message["content"]) if message.get("content") is not None else ""
                message_content = content_str.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$").replace("\n", "\\n").replace("\r", "\\r")
                
                st.components.v1.html(f"""
                <div style="text-align: right;">
                    <button id="copyBtn_normal_{idx}" onclick="handleCopyNormal_{idx}()" 
                            style="background: transparent; border: none; cursor: pointer; font-size: 1.2rem; padding: 0.5rem; opacity: 0.7; transition: all 0.2s; border-radius: 6px;"
                            onmouseover="this.style.opacity='1'; this.style.backgroundColor='rgba(0,0,0,0.05)'"
                            onmouseout="this.style.opacity='0.7'; this.style.backgroundColor='transparent'"
                            title="Copy message">
                        📋
                    </button>
                    <script>
                        function handleCopyNormal_{idx}() {{
                            const text = `{message_content}`;
                            const btn = document.getElementById('copyBtn_normal_{idx}');
                            
                            // Try modern Clipboard API
                            if (navigator.clipboard && window.isSecureContext) {{
                                navigator.clipboard.writeText(text).then(() => {{
                                    btn.innerHTML = '✅';
                                    btn.style.color = '#10b981';
                                    setTimeout(() => {{
                                        btn.innerHTML = '📋';
                                        btn.style.color = '';
                                    }}, 1500);
                                }}).catch(() => {{
                                    fallbackCopyNormal_{idx}(text, btn);
                                }});
                            }} else {{
                                fallbackCopyNormal_{idx}(text, btn);
                            }}
                        }}
                        
                        function fallbackCopyNormal_{idx}(text, btn) {{
                            const textarea = document.createElement('textarea');
                            textarea.value = text;
                            textarea.style.position = 'fixed';
                            textarea.style.top = '-9999px';
                            textarea.style.left = '-9999px';
                            document.body.appendChild(textarea);
                            textarea.focus();
                            textarea.select();
                            try {{
                                const success = document.execCommand('copy');
                                document.body.removeChild(textarea);
                                if (success) {{
                                    btn.innerHTML = '✅';
                                    btn.style.color = '#10b981';
                                    setTimeout(() => {{
                                        btn.innerHTML = '📋';
                                        btn.style.color = '';
                                    }}, 1500);
                                }}
                            }} catch (err) {{
                                document.body.removeChild(textarea);
                                alert('Copy failed. Please select the text manually.');
                            }}
                        }}
                    </script>
                </div>
                """, height=50)

    # Add spacer to push chat input to bottom
    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
    
    # Chat input for Normal mode - placed after all messages
    if prompt := st.chat_input("💬 Type your message here..."):
        # Add user message to chat history
        st.session_state.normal_messages.append({"role": "user", "content": prompt})
        
        # Display user message immediately
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get AI response with memory
        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking..."):
                try:
                    # Get response from chat chain (uses conversation memory)
                    response = get_chat_response(prompt, mode="normal")
                    
                    # Display AI response
                    st.markdown(response)
                    
                    # Copy icon - Direct copy on click for assistant response
                    col1, col2 = st.columns([9.5, 0.5])
                    with col1:
                        st.empty()
                    with col2:
                        msg_num = len(st.session_state.normal_messages)
                        response_escaped = response.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$").replace("\n", "\\n").replace("\r", "\\r")
                        
                        st.components.v1.html(f"""
                        <div style="text-align: right;">
                            <button id="copyAssistantBtn_normal_{msg_num}" onclick="handleCopyAssistantNormal_{msg_num}()" 
                                    style="background: transparent; border: none; cursor: pointer; font-size: 1.2rem; padding: 0.5rem; opacity: 0.7; transition: all 0.2s; border-radius: 6px;"
                                    onmouseover="this.style.opacity='1'; this.style.backgroundColor='rgba(0,0,0,0.05)'"
                                    onmouseout="this.style.opacity='0.7'; this.style.backgroundColor='transparent'"
                                    title="Copy message">
                                📋
                            </button>
                            <script>
                                function handleCopyAssistantNormal_{msg_num}() {{
                                    const text = `{response_escaped}`;
                                    const btn = document.getElementById('copyAssistantBtn_normal_{msg_num}');
                                    if (navigator.clipboard && window.isSecureContext) {{
                                        navigator.clipboard.writeText(text).then(() => {{
                                            btn.innerHTML = '✅';
                                            btn.style.color = '#10b981';
                                            setTimeout(() => {{ btn.innerHTML = '📋'; btn.style.color = ''; }}, 1500);
                                        }}).catch(() => {{ fallbackCopyAssistantNormal_{msg_num}(text, btn); }});
                                    }} else {{
                                        fallbackCopyAssistantNormal_{msg_num}(text, btn);
                                    }}
                                }}
                                function fallbackCopyAssistantNormal_{msg_num}(text, btn) {{
                                    const textarea = document.createElement('textarea');
                                    textarea.value = text;
                                    textarea.style.position = 'fixed';
                                    textarea.style.top = '-9999px';
                                    document.body.appendChild(textarea);
                                    textarea.select();
                                    document.execCommand('copy');
                                    document.body.removeChild(textarea);
                                    btn.innerHTML = '✅';
                                    btn.style.color = '#10b981';
                                    setTimeout(() => {{ btn.innerHTML = '📋'; btn.style.color = ''; }}, 1500);
                                }}
                            </script>
                        </div>
                        """, height=50)
                    
                    # Add assistant response to chat history
                    st.session_state.normal_messages.append({"role": "assistant", "content": response})
                    
                except Exception as e:
                    error_msg = f"❌ Sorry, I encountered an error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.normal_messages.append({"role": "assistant", "content": error_msg})
                    logging.error(f"Chat error: {str(e)}")
                    logging.error(traceback.format_exc())
                    st.exception(e)

# Add empty space at bottom for better UX
st.markdown("<br><br><br>", unsafe_allow_html=True)

