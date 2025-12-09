import streamlit as st
import requests
import json
from datetime import datetime
import os

# === CONFIGURATION ===
BACKEND_URL = "https://agentbackendservice-dfcpcudzeah4b6ae.northeurope-01.azurewebsites.net/api"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# Set page config
st.set_page_config(
    page_title="OmniFlow Assistant",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# === SIDEBAR CONFIGURATION ===
st.sidebar.title("⚙️ Configuration")

# User ID
user_id = st.sidebar.text_input(
    "User ID",
    value="default_user",
    help="Your unique user identifier"
)

# Category selector
categories = ["TM", "PS", "LO", "GEN", "ID", "PE", "UI", "ML", "SYS"]
selected_category = st.sidebar.selectbox(
    "Knowledge Category",
    categories,
    help="Select knowledge domain"
)

# File selector
st.sidebar.markdown("---")
st.sidebar.subheader("📁 File Management")

# Quick actions
col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("➕ Add Task"):
        st.session_state.quick_action = "add_task"
with col2:
    if st.button("📋 View Tasks"):
        st.session_state.quick_action = "view_tasks"

# === HELPER FUNCTIONS ===
def call_backend(endpoint: str, payload: dict) -> dict:
    """Call Azure backend with user context"""
    headers = {
        "X-User-Id": user_id,
        "Content-Type": "application/json"
    }
    try:
        # FIX: Don't append endpoint twice - BACKEND_URL already includes /api
        url = f"{BACKEND_URL}/{endpoint}"
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Backend error: {e}")
        return {"error": str(e)}

def send_to_llm(messages: list) -> str:
    """Send messages to LLM via backend proxy"""
    payload = {
        "message": messages[-1]["content"] if messages else "",
        "user_id": user_id,
        "thread_id": st.session_state.get("thread_id")
    }
    
    result = call_backend("tool_call_handler", payload)
    
    if "response" in result:
        st.session_state.thread_id = result.get("thread_id")
        return result["response"]
    return f"Error: {result.get('error', 'Unknown error')}"

def get_file_stats():
    """Get statistics for all user files"""
    result = call_backend("list_blobs", {"user_id": user_id})
    return result.get("blobs", [])

def read_file_content(filename: str):
    """Read a specific file"""
    result = call_backend("read_blob_file", {"file_name": filename})
    return result.get("data", [])

# === MAIN LAYOUT ===
# Main content area with two columns
main_col1, main_col2 = st.columns([3, 1])

with main_col1:
    st.title("🚀 OmniFlow Assistant")
    st.markdown(f"**User:** {user_id} | **Category:** {selected_category}")
    
    # Chat interface
    st.subheader("💬 Chat")
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = None
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Chat input with unique key
    prompt = st.chat_input("Ask me anything...", key="chat_input_unique")
    
    if prompt:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
        
        # Get LLM response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = send_to_llm(st.session_state.messages)
            st.write(response)
        
        # Store assistant response
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()

with main_col2:
    st.subheader("📊 Context")
    
    # File stats
    st.markdown("**📁 Your Files:**")
    files = get_file_stats()
    
    if files:
        for file in files[:5]:  # Show top 5
            st.caption(f"📄 {file}")
    else:
        st.caption("No files yet")
    
    # Today's tasks section
    st.markdown("---")
    st.markdown("**✅ Quick Stats:**")
    st.metric("Total Files", len(files))
    st.metric("Category", selected_category)
    
    # User info
    st.markdown("---")
    st.markdown("**👤 User Info:**")
    st.caption(f"ID: {user_id}")
    st.caption(f"Last: {datetime.now().strftime('%H:%M:%S')}")
