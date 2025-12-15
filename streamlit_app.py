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
REQUEST_TIMEOUT = 30

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

# === SIDEBAR - USER MANAGEMENT ===
st.sidebar.title("👤 User Management")

# Initialize user list in session state
if "user_list" not in st.session_state:
    st.session_state.user_list = ["default_user", "alice_123", "bob_456", "test_user"]

# Current user ID input
current_user = st.sidebar.text_input(
    "Current User ID",
    value=st.session_state.get("current_user", "default_user"),
    help="Your unique user identifier (3-64 chars, alphanumeric, _, -, .)"
)

# Validate user ID
import re
def validate_user_id(uid):
    if not uid or len(uid) < 3 or len(uid) > 64:
        return False
    return bool(re.match(r'^[a-zA-Z0-9._-]+$', uid))

if current_user != st.session_state.get("current_user"):
    if validate_user_id(current_user):
        st.session_state.current_user = current_user
        if current_user not in st.session_state.user_list:
            st.session_state.user_list.append(current_user)
        user_id = current_user
    else:
        st.sidebar.error("❌ Invalid user ID format")
        user_id = st.session_state.get("current_user", "default_user")
else:
    user_id = current_user

# Quick user switcher
st.sidebar.markdown("**Quick Switch:**")
selected_quick_user = st.sidebar.selectbox(
    "Select from existing users",
    st.session_state.user_list,
    index=st.session_state.user_list.index(user_id) if user_id in st.session_state.user_list else 0,
    label_visibility="collapsed"
)

if selected_quick_user != user_id:
    st.session_state.current_user = selected_quick_user
    st.rerun()

# Add new user
with st.sidebar.expander("➕ Add New User"):
    new_user_id = st.text_input("New User ID", key="new_user_input")
    create_default_files = st.checkbox("Create default files", value=True, 
                                       help="Create tasks.json, ideas.json, notes.json for new user")
    
    if st.button("Create User"):
        if validate_user_id(new_user_id):
            if new_user_id not in st.session_state.user_list:
                # Try to create user via backend (if endpoint exists)
                if create_default_files:
                    result = create_new_user(new_user_id)
                    if result.get("status") == "success":
                        st.success(f"✅ User '{new_user_id}' created with default files!")
                        st.caption(f"Created: {', '.join(result.get('files_created', []))}")
                    elif "error" in result and "404" in str(result.get("error", "")):
                        st.warning("⚠️ Backend endpoint not available. User added locally only.")
                    else:
                        st.warning(f"⚠️ Backend: {result.get('error', 'Unknown error')}")
                else:
                    st.info("ℹ️ User added (no backend files created)")
                
                # Add to local list
                st.session_state.user_list.append(new_user_id)
                st.session_state.current_user = new_user_id
                st.rerun()
            else:
                st.warning("⚠️ User already exists")
        else:
            st.error("❌ Invalid format: 3-64 chars, alphanumeric, _, -, .")

# User stats
st.sidebar.caption(f"👥 Total users: {len(st.session_state.user_list)}")

st.sidebar.markdown("---")

# Temperature control
st.sidebar.markdown("**🌡️ AI Settings:**")
temperature = st.sidebar.slider(
    "Temperature",
    min_value=0.0,
    max_value=2.0,
    value=1.0,
    step=0.1,
    help="Controls randomness: 0 = focused/deterministic, 2 = creative/random"
)
st.sidebar.caption(f"Current: {temperature}")

st.sidebar.markdown("---")

# Feature toggles
st.sidebar.markdown("**Features:**")
show_files = st.sidebar.checkbox("📁 File Browser", value=False)
show_history = st.sidebar.checkbox("📜 History", value=False)
show_data_manager = st.sidebar.checkbox("🗂️ Data Manager", value=False)

# === HELPER FUNCTIONS ===
def call_backend(endpoint: str, payload: dict = None, method: str = "POST") -> tuple:
    """Call Azure backend with user context and return response + timing"""
    headers = {
        "X-User-Id": user_id,
        "Content-Type": "application/json"
    }
    start_time = time.time()
    try:
        url = f"{BACKEND_URL}/{endpoint}?code={FUNCTION_KEY}"
        
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        else:
            response = requests.post(url, json=payload or {}, headers=headers, timeout=REQUEST_TIMEOUT)
        
        response.raise_for_status()
        elapsed = time.time() - start_time
        return response.json(), elapsed
    except requests.exceptions.RequestException as e:
        elapsed = time.time() - start_time
        return {"error": str(e)}, elapsed

def send_to_llm(messages: list, temp: float = 1.0) -> tuple:
    """Send messages to LLM via backend proxy, return response and stats"""
    payload = {
        "message": messages[-1]["content"] if messages else "",
        "user_id": user_id,
        "thread_id": st.session_state.get("thread_id"),
        "temperature": temp  # Include temperature (backend may use it in future)
    }
    
    result, elapsed = call_backend("tool_call_handler", payload)
    
    # Store response stats
    stats = {
        "response_time": elapsed,
        "timestamp": datetime.now(),
        "has_error": "error" in result,
        "tool_calls_count": result.get("tool_calls_count", 0),
        "thread_id": result.get("thread_id"),
        "temperature": temp
    }
    
    if "response" in result:
        st.session_state.thread_id = result.get("thread_id")
        return result["response"], stats
    return "Error communicating with assistant", stats

def get_user_files():
    """Get list of user's files"""
    result, _ = call_backend("list_blobs", {"user_id": user_id})
    return result.get("blobs", [])

def get_interaction_history(limit: int = 10):
    """Get user's conversation history"""
    url = f"{BACKEND_URL}/get_interaction_history?limit={limit}&code={FUNCTION_KEY}"
    headers = {"X-User-Id": user_id}
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def read_file_content(filename: str):
    """Read a specific file"""
    result, _ = call_backend("read_blob_file", {"file_name": filename})
    return result.get("data", [])

def add_data_entry(filename: str, entry: dict):
    """Add new data entry to file"""
    result, _ = call_backend("add_new_data", {
        "target_blob_name": filename,
        "new_entry": entry,
        "user_id": user_id
    })
    return result

def get_filtered_data(filename: str, key: str, value: str):
    """Get filtered data from file"""
    result, _ = call_backend("get_filtered_data", {
        "target_blob_name": filename,
        "key": key,
        "value": value,
        "user_id": user_id
    })
    return result

def create_new_user(new_user_id: str):
    """Create new user with basic file set (requires backend support)"""
    result, _ = call_backend("create_user", {
        "user_id": new_user_id,
        "create_default_files": True
    })
    return result

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
        total_tools = sum(s.get("tool_calls_count", 0) for s in st.session_state.stats_history)
        st.markdown(
            f'<div style="padding: 4px 0;">'
            f'<span class="stat-box">Last: {last_stats["response_time"]:.2f}s</span>'
            f'<span class="stat-box">Avg: {avg_time:.2f}s</span>'
            f'<span class="stat-box">Exchanges: {len(st.session_state.messages)//2}</span>'
            f'<span class="stat-box">Tools: {total_tools}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

st.markdown('</div>', unsafe_allow_html=True)

# Debug info panel (collapsible)
if st.session_state.debug_mode:
    with st.expander("🔍 Debug Information", expanded=True):
        col_d1, col_d2, col_d3, col_d4 = st.columns(4)
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
        with col_d4:
            if st.session_state.stats_history:
                total_tools = sum(s.get("tool_calls_count", 0) for s in st.session_state.stats_history)
                st.metric("Total Tool Calls", total_tools)
                st.metric("Temperature", "N/A (not exposed)")

st.markdown("---")

# === OPTIONAL PANELS ===
if show_files:
    with st.expander("📁 File Browser", expanded=True):
        if st.button("🔄 Refresh Files"):
            st.rerun()
        
        files = get_user_files()
        if files:
            st.write(f"**Found {len(files)} file(s):**")
            for file in files:
                col_f1, col_f2 = st.columns([3, 1])
                with col_f1:
                    st.text(f"📄 {file}")
                with col_f2:
                    if st.button("View", key=f"view_{file}"):
                        content = read_file_content(file)
                        st.json(content)
        else:
            st.info("No files found for this user")

if show_history:
    with st.expander("📜 Conversation History", expanded=True):
        history_limit = st.slider("Number of interactions", 5, 50, 10)
        if st.button("🔄 Load History"):
            history = get_interaction_history(history_limit)
            if "interactions" in history:
                st.write(f"**Loaded {len(history['interactions'])} interaction(s):**")
                for idx, interaction in enumerate(reversed(history["interactions"])):
                    st.markdown(f"**#{idx+1}** - {interaction.get('timestamp', 'N/A')}")
                    st.text(f"User: {interaction.get('user_message', '')[:100]}...")
                    st.text(f"Assistant: {interaction.get('assistant_response', '')[:100]}...")
                    if interaction.get('tool_calls'):
                        st.caption(f"🔧 {len(interaction['tool_calls'])} tool call(s)")
                    st.markdown("---")
            else:
                st.error(f"Error: {history.get('error', 'Unknown error')}")

if show_data_manager:
    with st.expander("🗂️ Data Manager", expanded=True):
        st.subheader("Add New Entry")
        dm_file = st.text_input("File name (e.g., tasks.json)")
        dm_entry_json = st.text_area("Entry (JSON format)", '{"id": "1", "content": "example"}')
        
        if st.button("➕ Add Entry"):
            try:
                entry = json.loads(dm_entry_json)
                result = add_data_entry(dm_file, entry)
                if result.get("status") == "success":
                    st.success(f"✅ {result.get('message')}")
                else:
                    st.error(f"❌ {result.get('error', 'Unknown error')}")
            except json.JSONDecodeError:
                st.error("Invalid JSON format")
        
        st.markdown("---")
        st.subheader("Query Data")
        qd_file = st.text_input("File to query")
        qd_col1, qd_col2 = st.columns(2)
        with qd_col1:
            qd_key = st.text_input("Key")
        with qd_col2:
            qd_value = st.text_input("Value")
        
        if st.button("🔍 Query"):
            result = get_filtered_data(qd_file, qd_key, qd_value)
            if result.get("status") == "success":
                st.success(f"Found {result.get('count', 0)} of {result.get('total', 0)} entries")
                st.json(result.get("data", []))
            else:
                st.error(f"❌ {result.get('error', 'Unknown error')}")

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
                tools_used = stats.get('tool_calls_count', 0)
                st.caption(f"⏱️ {stats['response_time']:.2f}s | 🔧 {tools_used} tools | {stats['timestamp'].strftime('%H:%M:%S')}")

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
            response, stats = send_to_llm(st.session_state.messages, temperature)
        st.write(response)
        
        # Show response time and tool usage
        if st.session_state.debug_mode:
            tools_used = stats.get('tool_calls_count', 0)
            temp_used = stats.get('temperature', 1.0)
            st.caption(f"⏱️ {stats['response_time']:.2f}s | 🔧 {tools_used} tools | 🌡️ {temp_used}")
    
    # Store assistant response and stats
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.session_state.stats_history.append(stats)
    st.rerun()
