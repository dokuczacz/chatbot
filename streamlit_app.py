import streamlit as st
import requests
import json
from datetime import datetime
import os
import time

# === CONFIGURATION ===
BACKEND_URL = "https://agentbackendservice-dfcpcudzeah4b6ae.northeurope-01.azurewebsites.net/api"
FUNCTION_KEY = os.environ.get("AZURE_FUNCTION_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# Set page config with light theme
st.set_page_config(
    page_title="OmniFlow Assistant",
    page_icon="🚀",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# === CUSTOM CSS FOR LIGHT THEME ===
st.markdown("""
<style>
    /* Light theme styling */
    .stApp {
        background-color: #ffffff;
    }
    
    .main .block-container {
        background-color: #ffffff;
        padding-top: 2rem;
    }
    
    /* Debug panel styling */
    .debug-panel {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 20px;
    }
    
    .debug-icon {
        display: inline-block;
        margin-right: 15px;
        font-size: 1.2em;
    }
    
    .stat-box {
        background-color: #e9ecef;
        border-radius: 6px;
        padding: 8px 12px;
        display: inline-block;
        margin-right: 10px;
        font-size: 0.9em;
    }
    
    /* Chat message styling */
    .stChatMessage {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
    }
    
    /* Input styling */
    .stChatInput {
        background-color: #ffffff;
        border: 2px solid #dee2e6;
    }
</style>
""", unsafe_allow_html=True)

# === SIMPLE SIDEBAR ===
st.sidebar.title("⚙️ Settings")

# User ID only
user_id = st.sidebar.text_input(
    "User ID",
    value="default_user",
    help="Your unique user identifier"
)

# === HELPER FUNCTIONS ===
def call_backend(endpoint: str, payload: dict) -> tuple:
    """Call Azure backend with user context and return response + timing"""
    headers = {
        "X-User-Id": user_id,
        "Content-Type": "application/json"
    }
    start_time = time.time()
    try:
        # Include function key for authentication
        url = f"{BACKEND_URL}/{endpoint}?code={FUNCTION_KEY}"
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        elapsed = time.time() - start_time
        return response.json(), elapsed
    except requests.exceptions.RequestException as e:
        elapsed = time.time() - start_time
        st.error(f"Backend error: {e}")
        return {"error": str(e)}, elapsed

def send_to_llm(messages: list) -> tuple:
    """Send messages to LLM via backend proxy, return response and stats"""
    payload = {
        "message": messages[-1]["content"] if messages else "",
        "user_id": user_id,
        "thread_id": st.session_state.get("thread_id")
    }
    
    result, elapsed = call_backend("tool_call_handler", payload)
    
    # Store response stats
    stats = {
        "response_time": elapsed,
        "timestamp": datetime.now(),
        "has_error": "error" in result
    }
    
    if "response" in result:
        st.session_state.thread_id = result.get("thread_id")
        return result["response"], stats
    return "Error communicating with assistant", stats

# === MAIN LAYOUT ===
st.title("🚀 OmniFlow Assistant")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "stats_history" not in st.session_state:
    st.session_state.stats_history = []
if "debug_mode" not in st.session_state:
    st.session_state.debug_mode = False

# === DEBUG/STATISTICS PANEL ===
st.markdown('<div class="debug-panel">', unsafe_allow_html=True)

# Debug icons and controls
col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 4])

with col1:
    if st.button("🐛", help="Toggle Debug Mode"):
        st.session_state.debug_mode = not st.session_state.debug_mode

with col2:
    st.markdown('<span class="debug-icon">⏱️</span>', unsafe_allow_html=True)

with col3:
    st.markdown('<span class="debug-icon">📊</span>', unsafe_allow_html=True)

with col4:
    if st.button("🔄", help="Clear Chat"):
        st.session_state.messages = []
        st.session_state.stats_history = []
        st.rerun()

with col5:
    # Display current stats
    if st.session_state.stats_history:
        last_stats = st.session_state.stats_history[-1]
        avg_time = sum(s["response_time"] for s in st.session_state.stats_history) / len(st.session_state.stats_history)
        st.markdown(
            f'<div style="padding: 4px 0;">'
            f'<span class="stat-box">Last: {last_stats["response_time"]:.2f}s</span>'
            f'<span class="stat-box">Avg: {avg_time:.2f}s</span>'
            f'<span class="stat-box">Total: {len(st.session_state.messages)//2} exchanges</span>'
            f'</div>',
            unsafe_allow_html=True
        )

st.markdown('</div>', unsafe_allow_html=True)

# Debug info panel (collapsible)
if st.session_state.debug_mode:
    with st.expander("🔍 Debug Information", expanded=True):
        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            st.metric("User ID", user_id)
            st.metric("Thread ID", st.session_state.thread_id or "Not started")
        with col_d2:
            st.metric("Messages", len(st.session_state.messages))
            if st.session_state.stats_history:
                error_count = sum(1 for s in st.session_state.stats_history if s["has_error"])
                st.metric("Errors", error_count)
        with col_d3:
            st.metric("Backend", "Azure Functions")
            st.metric("Status", "🟢 Connected" if FUNCTION_KEY else "⚠️ No Key")

st.markdown("---")

# === CHAT INTERFACE ===
# Display chat history with scrolling
for idx, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.write(message["content"])
        
        # Show stats for assistant messages in debug mode
        if message["role"] == "assistant" and st.session_state.debug_mode:
            stats_idx = idx // 2
            if stats_idx < len(st.session_state.stats_history):
                stats = st.session_state.stats_history[stats_idx]
                st.caption(f"⏱️ Response time: {stats['response_time']:.2f}s | {stats['timestamp'].strftime('%H:%M:%S')}")

# Chat input
prompt = st.chat_input("Ask me anything...", key="chat_input_unique")

if prompt:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    
    # Get LLM response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response, stats = send_to_llm(st.session_state.messages)
        st.write(response)
        
        # Show response time
        if st.session_state.debug_mode:
            st.caption(f"⏱️ Response time: {stats['response_time']:.2f}s")
    
    # Store assistant response and stats
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.session_state.stats_history.append(stats)
    st.rerun()
