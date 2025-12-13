import streamlit as st
import requests
import os

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="AeroMate", page_icon="✈️")

# --- 1. Session State Initialization ---
if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 2.1. Load Chat History Function ---
def load_chat_history(user_id):
    """
    Fetches chat history from the backend for a specific user.
    Returns a list of messages (empty if new user or error).
    """
    try:
        url = f"{BACKEND_URL}/history/{user_id}"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            return data.get("history", [])
        else:
            st.error(f"Error loading history: {response.text}")
            return []
            
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to Backend to load history. Is it running?")
        return []
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return []
    
# --- 2. Login Screen (The Gatekeeper) ---
if not st.session_state.user_id:
    st.title("✈️ AeroMate Login")
    st.write("Enter your User ID to access your personal travel assistant.")
    
    with st.form("login_form"):
        # Changed input label to generic "User ID"
        user_id_input = st.text_input("User ID", placeholder="eg. john_doe, user_123, or email")
        submitted = st.form_submit_button("Start Chatting")
        
        if submitted and user_id_input:
            # Show a spinner while we fetch data
            with st.spinner("Syncing your travel history..."):
                history = load_chat_history(user_id_input)
                
            # Update Session State
            st.session_state.user_id = user_id_input
            st.session_state.messages = history
            st.rerun()

# --- 3. Chat Interface (Only shows if logged in) ---
else:
    with st.sidebar:
        st.write(f"Logged in as: **{st.session_state.user_id}**")
        if st.button("Logout"):
            st.session_state.user_id = None
            st.session_state.messages = []
            st.rerun()

    st.title("✈️ AeroMate")
    st.caption("""Your smart flight companion managing bookings, tracking travel plans, and providing immediate assistance whenever your journey needs it
    """)

    # Display previous messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Handle User Input
    if prompt := st.chat_input("How can I help with your travel?"):
        # Show user message immediately
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Call the Backend API
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("Thinking...") 
            full_response = ""
            
            try:
                # payload uses the User ID as the thread_id
                payload = {
                    "thread_id": st.session_state.user_id,
                    "message": prompt
                }

                # # Call Backend
                # with requests.post(f"{BACKEND_URL}/chat", json=payload, stream=True) as response:
                #     if response.status_code == 200:
                #         full_response = response.json().get("response", "No response text.")
                #         message_placeholder.markdown(full_response)
                #     else:
                #         message_placeholder.error(f"Error {response.status_code}: {response.text}")
                
                # Call Backend with streaming
                with requests.post(f"{BACKEND_URL}/chatstream", json=payload, stream=True) as response:
                    if response.status_code == 200:
                        message_placeholder.empty()
                        for chunk in response.iter_content(chunk_size=1024):
                            if chunk:
                                decoded_chunk = chunk.decode("utf-8")
                                full_response += decoded_chunk
                                message_placeholder.markdown(full_response + "▌")
                        
                        message_placeholder.markdown(full_response)
                    else:
                        message_placeholder.error(f"Error {response.status_code}: {response.text}")
            
            except requests.exceptions.ConnectionError:
                message_placeholder.error("Cannot connect to Backend. Is it running?")
            except Exception as e:
                message_placeholder.error(f"An error occurred: {e}")

        # Save assistant response to history
        if full_response:
            st.session_state.messages.append({"role": "assistant", "content": full_response})