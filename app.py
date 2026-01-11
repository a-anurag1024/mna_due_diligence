import streamlit as st
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables from .env file FIRST (before importing agents)
load_dotenv()

# Import after loading env vars so agents can access OPENAI_API_KEY
from mna_due_diligence.agents.master import MultiAgentClient

st.set_page_config(page_title="Agentic Audit Team", layout="wide")
st.title("🤖 Multi-Agent Audit Team")

# Check MCP server URL
mcp_url = os.getenv("MCP_SSE_URL", "http://localhost:8000/sse")
if not mcp_url:
    st.error("MCP_SSE_URL environment variable not set!")
    st.stop()

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_complete" not in st.session_state:
    st.session_state.conversation_complete = False
if "tool_logs" not in st.session_state:
    st.session_state.tool_logs = []

# Add reset button in sidebar
with st.sidebar:
    st.header("🔄 Session Control")
    if st.button("Reset Chat", type="primary", use_container_width=True):
        st.session_state.messages = []
        st.session_state.conversation_complete = False
        st.session_state.tool_logs = []
        st.rerun()
    
    if st.session_state.messages:
        st.metric("Messages", len(st.session_state.messages))
        if st.session_state.conversation_complete:
            st.success("✅ Session Complete")
        else:
            st.info("🔄 Session Active")

# Draw History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # Show tool logs for assistant messages
        if msg["role"] == "assistant" and "tool_logs" in msg and msg["tool_logs"]:
            with st.status("Tool Calls & Execution Log", state="complete", expanded=True):
                for log in msg["tool_logs"]:
                    st.write(log)

# --- THE STREAMING LOGIC ---
# Only allow new input if conversation is not complete
if not st.session_state.conversation_complete:
    if prompt := st.chat_input("Assign a task to the team..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            # 1. Create a Status Container (The "Live Log")
            status_container = st.status("Team is working...", expanded=True)
            
            # 2. Define the callback that updates the log and stores it
            def update_status(msg):
                status_container.write(msg)
                st.session_state.tool_logs.append(msg)

            # 3. Run the Team
            response_placeholder = st.empty()
            
            try:
                client = MultiAgentClient(sse_url=mcp_url)
                
                # Run the async generator
                async def run_stream():
                    full_response = ""
                    async for chunk in client.run_audit(prompt, update_status):
                        # Each chunk is an incremental text delta
                        full_response += chunk
                        response_placeholder.markdown(full_response + "▌")
                    return full_response
                
                full_response = asyncio.run(run_stream())
                
                # Finalize
                status_container.update(label="Audit Complete!", state="complete", expanded=True)
                response_placeholder.markdown(full_response)
                
                # Store the response with tool logs
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": full_response,
                    "tool_logs": st.session_state.tool_logs.copy()
                })
                
                # Mark conversation as complete
                st.session_state.conversation_complete = True
                st.rerun()

            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                st.error(f"Team Failure: {e}")
                st.error(f"Full error:\n```\n{error_details}\n```")
                status_container.update(label="Failed", state="error", expanded=True)
else:
    # Disable input when conversation is complete
    st.chat_input("Assign a task to the team...", disabled=True)