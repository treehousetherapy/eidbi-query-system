# eidbi-query-system/frontend/streamlit_app.py

import streamlit as st
import requests
import json
import os
import time
import logging
from typing import Dict, Any, Optional
import pandas as pd
import datetime

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s')
logger = logging.getLogger(__name__)

# --- Application Version ---
APP_VERSION = "1.1.2"
APP_NAME = "EIDBI Query Assistant"

# --- Configuration ---
# Allow configuration from environment variables
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
DEFAULT_NUM_RESULTS = int(os.getenv("DEFAULT_NUM_RESULTS", "3"))
MAX_NUM_RESULTS = int(os.getenv("MAX_NUM_RESULTS", "10"))
TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT", "30"))

# --- API Endpoints ---
QUERY_ENDPOINT = f"{BACKEND_URL}/query"
SIMPLE_QUERY_ENDPOINT = f"{BACKEND_URL}/simple-answer"
HEALTH_ENDPOINT = f"{BACKEND_URL}/health"

# --- Sample Queries ---
SAMPLE_QUERIES = [
    "Who is eligible for EIDBI services?",
    "What is the process to become an EIDBI provider?",
    "What services are covered under EIDBI?",
    "How can I find an EIDBI provider near me?",
    "What qualifications do EIDBI providers need?"
]

# --- Init Session State ---
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False

if 'query_text' not in st.session_state:
    st.session_state.query_text = ""

if 'run_query' not in st.session_state:
    st.session_state.run_query = False
    
if 'result' not in st.session_state:
    st.session_state.result = None
    
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

if 'show_welcome' not in st.session_state:
    st.session_state.show_welcome = True

# --- Custom CSS ---
st.set_page_config(
    layout="wide", 
    page_title=f"{APP_NAME}", 
    page_icon="🤖",
    initial_sidebar_state="expanded"
)

# Apply ChatGPT-style CSS
st.markdown("""
<style>
    /* Main Container Styles - ChatGPT-like */
    .main .block-container {
        padding-top: 0;
        padding-bottom: 0;
        max-width: 1000px;
    }
    
    /* Typography */
    body {
        font-family: 'Söhne', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', sans-serif;
        color: #374151;
    }
    h1 {
        color: #202123;
        font-weight: 700;
        margin-bottom: 0;
        font-size: 2rem;
    }
    h2 {
        color: #202123;
        margin-top: 1rem;
        font-weight: 600;
    }
    h3 {
        color: #202123;
        font-weight: 600;
    }
    
    /* Chat Container */
    .chat-container {
        display: flex;
        flex-direction: column;
        gap: 0px;
        padding-bottom: 40px;
    }
    
    /* Individual Message Styles */
    .user-message-container, .assistant-message-container {
        display: flex;
        padding: 1.5rem 1rem;
        width: 100%;
    }
    
    .user-message-container {
        background-color: #FFFFFF;
    }
    
    .assistant-message-container {
        background-color: #F7F7F8;
    }
    
    .avatar {
        width: 30px;
        height: 30px;
        border-radius: 0.125rem;
        display: flex;
        justify-content: center;
        align-items: center;
        margin-right: 1rem;
        flex-shrink: 0;
    }
    
    .user-avatar {
        background-color: #5436DA;
        color: white;
    }
    
    .assistant-avatar {
        background-color: #11A37F;
        color: white;
    }
    
    .message-content {
        display: flex;
        flex-direction: column;
        flex-grow: 1;
        width: calc(100% - 50px);
    }
    
    .message-text {
        width: 100%;
        line-height: 1.5;
    }
    
    /* Input Container */
    .input-container {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        margin: 0 auto;
        max-width: 1000px;
        padding: 1rem;
        background: white;
        border-top: 1px solid #E5E7EB;
        z-index: 100;
    }
    
    .stTextArea>div>div>textarea {
        border-radius: 0.75rem;
        border: 1px solid #E5E7EB;
        box-shadow: 0 0 10px rgba(0, 0, 0, 0.05);
        font-size: 1rem;
        font-family: 'Söhne', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', sans-serif;
        padding: 14px 45px 14px 14px;
        max-height: 200px;
        overflow-y: auto;
    }
    
    /* Send Button Styling */
    .send-button {
        position: absolute;
        bottom: 22px;
        right: 25px;
        background-color: #ECECF1;
        color: #555;
        width: 32px;
        height: 32px;
        border-radius: 0.375rem;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        box-shadow: none;
        border: none;
        transition: all 0.2s ease;
    }
    
    .send-button-active {
        background-color: #11A37F;
        color: white;
    }
    
    /* Sample Prompts */
    .sample-prompt {
        background-color: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 0.75rem;
        padding: 0.75rem 1rem;
        margin-bottom: 0.75rem;
        cursor: pointer;
        transition: all 0.2s ease;
        text-align: center;
    }
    .sample-prompt:hover {
        background-color: #F9FAFB;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }
    
    /* Welcome Screen */
    .welcome-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        margin-top: 6rem;
        text-align: center;
    }
    
    .welcome-title {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 1.5rem;
    }
    
    .examples-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 0.75rem;
        max-width: 700px;
        margin: 2rem auto;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #202123;
        color: white;
    }
    section[data-testid="stSidebar"] > div {
        padding: 2rem 1rem;
    }
    
    /* Remove padding for better mobile view */
    @media (max-width: 768px) {
        .main .block-container {
            padding: 0;
        }
    }
    
    /* Hide default Streamlit items */
    #MainMenu, footer, header {
        visibility: hidden;
    }
    
    /* Dark Mode Styles */
    /* Will be activated via JavaScript */
    .dark-mode {
        background-color: #343541;
        color: white;
    }
    
    .dark-mode .user-message-container {
        background-color: #343541;
    }
    
    .dark-mode .assistant-message-container {
        background-color: #444654;
    }
    
    .dark-mode .stTextArea>div>div>textarea {
        background-color: #40414F;
        border-color: #565869;
        color: white;
    }
    
    .dark-mode .stTextArea>div>div>textarea::placeholder {
        color: #ACACBE;
    }
    
    .dark-mode .welcome-container {
        color: white;
    }
    
    .dark-mode .sample-prompt {
        background-color: #3E3F4B;
        border-color: #565869;
        color: white;
    }
    
    .dark-mode .sample-prompt:hover {
        background-color: #444654;
    }
    
    .dark-mode .send-button {
        background-color: #40414F;
        color: #ACACBE;
    }
    
    .dark-mode .send-button-active {
        background-color: #19C37D;
        color: white;
    }
    
    .dark-mode .input-container {
        background-color: #343541;
        border-top-color: #565869;
    }
    
    /* New Chat Button */
    .new-chat-button {
        background-color: #202123;
        color: white;
        border: 1px solid #4D4D4F;
        border-radius: 0.375rem;
        padding: 0.75rem 1rem;
        text-align: left;
        cursor: pointer;
        transition: all 0.2s ease;
        margin-bottom: 1rem;
        font-size: 0.9rem;
    }
    .new-chat-button:hover {
        background-color: #2A2B32;
    }
</style>
""", unsafe_allow_html=True)

# --- Helper Functions ---
def check_backend_health() -> Dict[str, Any]:
    """Check if the backend is healthy and return status information."""
    try:
        response = requests.get(HEALTH_ENDPOINT, timeout=TIMEOUT_SECONDS)
        if response.status_code == 200:
            return {
                "healthy": True,
                "status": "Connected",
                "version": response.json().get("version", "Unknown"),
                "message": None
            }
        else:
            return {
                "healthy": False,
                "status": "Error",
                "version": None,
                "message": f"Backend returned status code {response.status_code}"
            }
    except requests.exceptions.ConnectionError:
        return {
            "healthy": False,
            "status": "Disconnected",
            "version": None,
            "message": f"Could not connect to backend at {BACKEND_URL}"
        }
    except Exception as e:
        return {
            "healthy": False,
            "status": "Error",
            "version": None,
            "message": str(e)
        }

def query_backend(query_text: str, num_results: int, use_simple_query: bool) -> Dict[str, Any]:
    """
    Query the backend API and handle errors gracefully.
    
    Args:
        query_text: The user's query text
        num_results: Number of context chunks to retrieve
        use_simple_query: Whether to use the simple query endpoint
        
    Returns:
        Dictionary with query results or error information
    """
    start_time = time.time()
    endpoint = SIMPLE_QUERY_ENDPOINT if use_simple_query else QUERY_ENDPOINT
    
    try:
        # Prepare the payload based on the endpoint
        if use_simple_query:
            payload = {"query_text": query_text}
        else:
            payload = {
                "query_text": query_text,
                "num_results": num_results
            }
        
        logger.info(f"Sending query to {endpoint}: {query_text}")
        response = requests.post(endpoint, json=payload, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        
        result = response.json()
        response_time = time.time() - start_time
        
        return {
            "success": True,
            "data": result,
            "response_time": response_time,
            "error": None
        }
        
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error when querying {endpoint}")
        return {
            "success": False,
            "data": None,
            "response_time": time.time() - start_time,
            "error": f"Could not connect to the backend at {BACKEND_URL}. Is it running?"
        }
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout when querying {endpoint}")
        return {
            "success": False,
            "data": None,
            "response_time": TIMEOUT_SECONDS,
            "error": f"Request timed out after {TIMEOUT_SECONDS} seconds. The backend may be overloaded."
        }
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error when querying {endpoint}: {str(e)}")
        return {
            "success": False,
            "data": None,
            "response_time": time.time() - start_time,
            "error": f"Error communicating with backend: {str(e)}"
        }
        
    except Exception as e:
        logger.error(f"Unexpected error when querying {endpoint}: {str(e)}", exc_info=True)
        return {
            "success": False,
            "data": None,
            "response_time": time.time() - start_time,
            "error": f"An unexpected error occurred: {str(e)}"
        }

def add_to_chat_history(role: str, content: str):
    """Add a message to the chat history in session state"""
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Add message to history
    st.session_state.chat_history.append({
        "role": role,
        "content": content,
        "timestamp": datetime.datetime.now()
    })

def clear_chat_history():
    """Clear the chat history"""
    st.session_state.chat_history = []
    st.session_state.show_welcome = True

def toggle_dark_mode():
    """Toggle between light and dark mode"""
    st.session_state.dark_mode = not st.session_state.dark_mode

# --- Sidebar ---
with st.sidebar:
    # App title
    st.markdown(f"""
    <div style="color: white; margin-bottom: 2rem;">
        <h1 style="color: white; font-size: 1.5rem; margin-bottom: 0.5rem;">{APP_NAME}</h1>
        <p style="opacity: 0.8; font-size: 0.9rem;">v{APP_VERSION}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # New Chat button
    if st.button("+ New Chat", key="new_chat", use_container_width=True):
        clear_chat_history()
        st.rerun()
    
    st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)
    
    # Settings section
    st.markdown("<p style='color: #8E8EA0; font-size: 0.8rem; margin-bottom: 0.5rem;'>SETTINGS</p>", unsafe_allow_html=True)
    
    # Dark mode toggle
    dark_mode = st.toggle("Dark Mode", value=st.session_state.dark_mode, key="dark_mode_toggle")
    if dark_mode != st.session_state.dark_mode:
        toggle_dark_mode()
        st.rerun()
    
    # Use simple query option
    use_simple_query = st.toggle(
        "Simple Mode (no document retrieval)", 
        value=False,
        help="Uses general knowledge instead of retrieving specific documents"
    )
    
    # Context size slider
    num_results = st.slider(
        "Context chunks", 
        min_value=1, 
        max_value=MAX_NUM_RESULTS, 
        value=DEFAULT_NUM_RESULTS,
        help="Number of relevant text chunks to retrieve"
    )
    
    # Backend health status
    backend_health = check_backend_health()
    
    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
    st.markdown("<p style='color: #8E8EA0; font-size: 0.8rem; margin-bottom: 0.5rem;'>SYSTEM STATUS</p>", unsafe_allow_html=True)
    
    if backend_health["healthy"]:
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 0.5rem;">
            <div style="width: 8px; height: 8px; border-radius: 50%; background-color: #10A37F;"></div>
            <span style="color: white;">Backend Connected</span>
        </div>
        """, unsafe_allow_html=True)
        st.caption(f"Version: {backend_health['version']}")
    else:
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 0.5rem;">
            <div style="width: 8px; height: 8px; border-radius: 50%; background-color: #FF4B4B;"></div>
            <span style="color: white;">Backend Disconnected</span>
        </div>
        """, unsafe_allow_html=True)
        if backend_health["message"]:
            st.caption(backend_health["message"])
    
    # Bottom section with credits
    st.markdown("""
    <div style="position: absolute; bottom: 20px; left: 20px; right: 20px; color: #8E8EA0; font-size: 0.8rem;">
        <p>Created for Minnesota EIDBI Program</p>
    </div>
    """, unsafe_allow_html=True)

# --- Main Content Area ---
# JavaScript to apply dark mode class
if st.session_state.dark_mode:
    st.markdown("""
    <script>
        // Add dark-mode class to body
        document.querySelector('body').classList.add('dark-mode');
    </script>
    """, unsafe_allow_html=True)

# Welcome screen when no chat history
if st.session_state.show_welcome and not st.session_state.chat_history:
    st.markdown("""
    <div class="welcome-container">
        <h1 class="welcome-title">EIDBI Assistant</h1>
        <p>Ask me anything about Minnesota's Early Intensive Developmental and Behavioral Intervention program.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<div class='examples-grid'>", unsafe_allow_html=True)
    
    # Display sample queries in a grid
    for query in SAMPLE_QUERIES:
        if st.button(query, key=f"sample_{query}", use_container_width=True):
            st.session_state.query_text = query
            st.session_state.run_query = True
            st.session_state.show_welcome = False
    
    st.markdown("</div>", unsafe_allow_html=True)

# Chat interface - display history
if st.session_state.chat_history:
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    for message in st.session_state.chat_history:
        role = message["role"]
        content = message["content"]
        
        if role == "user":
            st.markdown(f"""
            <div class="user-message-container">
                <div class="avatar user-avatar">👤</div>
                <div class="message-content">
                    <div class="message-text">{content}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:  # assistant
            st.markdown(f"""
            <div class="assistant-message-container">
                <div class="avatar assistant-avatar">🤖</div>
                <div class="message-content">
                    <div class="message-text">{content}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# User input area (fixed at bottom)
st.markdown('<div class="input-container">', unsafe_allow_html=True)

query_text = st.text_area(
    "Message EIDBI Assistant",
    value=st.session_state.query_text,
    height=68,
    placeholder="Message EIDBI Assistant...",
    label_visibility="collapsed"
)

# Create a button that looks like the send icon
has_content = len(query_text.strip()) > 0
button_class = "send-button send-button-active" if has_content else "send-button"
button_icon = "➤"

st.markdown(f"""
<button class="{button_class}" id="send-button" {'disabled' if not has_content else ''}>
    {button_icon}
</button>
""", unsafe_allow_html=True)

# Detect Enter key press and simulate button click
st.markdown("""
<script>
    // Simulate button click when Enter is pressed without Shift
    const textarea = document.querySelector('textarea');
    textarea.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            const sendButton = document.querySelector('button[data-testid="stButton"]');
            sendButton.click();
        }
    });
</script>
""", unsafe_allow_html=True)

# Hidden button to trigger the action
send_query = st.button("Send", key="send_query")

if send_query and query_text.strip():
    user_query = query_text.strip()
    st.session_state.query_text = ""  # Clear the input
    st.session_state.show_welcome = False
    
    # Add user message to chat
    add_to_chat_history("user", user_query)
    
    # Show a temporary loading message
    with st.spinner(""):
        # Query the backend
        result = query_backend(user_query, num_results, use_simple_query)
        
        if result["success"]:
            answer = result["data"].get("answer", "I'm sorry, I couldn't generate an answer. Please try again.")
            # Add assistant message to chat
            add_to_chat_history("assistant", answer)
        else:
            error_message = result.get("error", "Something went wrong. Please try again later.")
            # Add error message to chat
            add_to_chat_history("assistant", f"Error: {error_message}")
    
    # Rerun to update the UI
    st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# Add padding at the bottom to ensure the input box doesn't cover content
st.markdown("<div style='height: 120px;'></div>", unsafe_allow_html=True) 