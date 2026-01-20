import streamlit as st
import pandas as pd
import asyncio
import json
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command
from langgraph.errors import NodeInterrupt

from mna_due_diligence.agents.cerberus import cerberus_agent
from mna_due_diligence.agents.cerberus.utils import CerberusMindLogger

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Cerberus VDR Auditor",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SESSION STATE INITIALIZATION ---
if "messages" not in st.session_state:
    st.session_state.messages = []  # Chat history
if "risk_register" not in st.session_state:
    st.session_state.risk_register = [] # Global risks
if "logs" not in st.session_state:
    st.session_state.logs = [] # Streaming logs
if "thread_id" not in st.session_state:
    st.session_state.thread_id = "session_1" # Fixed ID for demo persistence
if "awaiting_input" not in st.session_state:
    st.session_state.awaiting_input = False # Track HITL state
if "interrupt_value" not in st.session_state:
    st.session_state.interrupt_value = None # Store the question asked by agent

# --- SIDEBAR: RISKS & LOGS ---
with st.sidebar:
    st.header("🛡️ Risk Register")
    
    # 1. RISK TABLE
    if st.session_state.risk_register:
        # Convert list of dicts to DataFrame
        df = pd.DataFrame(st.session_state.risk_register)
        
        # Simple styling: Highlight High Severity
        def highlight_risk(val):
            color = 'red' if val in ['High', 'Critical'] else 'black'
            return f'color: {color}'
            
        st.dataframe(
            df[["filename", "risk_category", "severity"]],
            use_container_width=True,
            hide_index=True
        )
        
        # Detail View Expander
        with st.expander("Risk Details"):
            for r in st.session_state.risk_register:
                st.markdown(f"**{r['filename']}** ({r['severity']})")
                st.caption(f"**Category:** {r['risk_category']}")
                st.caption(f"Reasoning: {r['reasoning']}")
                st.caption(f"Evidence: *\"{r['evidence_quote']}\"*")
                st.divider()
    else:
        st.info("No risks identified yet.")

# --- MAIN: CHAT INTERFACE ---
st.title("Cerberus: M&A Deal Due Diligence Auditor")

# 1. Display Chat History
for msg in st.session_state.messages:
    if isinstance(msg, HumanMessage):
        with st.chat_message("user"):
            st.markdown(msg.content)
    elif isinstance(msg, AIMessage):
        with st.chat_message("assistant"):
            st.markdown(msg.content)

# 2. Handle HITL Input (If Agent is Paused)
if st.session_state.awaiting_input:
    with st.chat_message("assistant"):
        st.warning(f"🛑 **APPROVAL REQUIRED:** {st.session_state.interrupt_value}")
        
    # Input for approval
    approval = st.chat_input("Reply to the agent (e.g., 'Yes', 'No', 'Proceed')...")
    
    if approval:
        # User replied to the pause
        st.session_state.messages.append(HumanMessage(content=approval))
        with st.chat_message("user"):
            st.markdown(approval)
            
        # RESUME EXECUTION
        st.session_state.awaiting_input = False
        
        # We invoke with COMMAND to resume
        # Note: We need to run this in the async loop below
        user_input = Command(resume=approval)
        run_agent = True
    else:
        run_agent = False # Wait for input

# 3. Handle Normal Input
elif prompt := st.chat_input("Ask Cerberus to audit files..."):
    st.session_state.messages.append(HumanMessage(content=prompt))
    with st.chat_message("user"):
        st.markdown(prompt)
    
    user_input = {"messages": [HumanMessage(content=prompt)]}
    run_agent = True

else:
    run_agent = False


# --- AGENT EXECUTION LOOP ---
if run_agent:
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        
        # Create a live status container for log display
        status_container = st.status("🧠 Cerberus Mind - Processing...", expanded=True)
        
        # Define callback in the Streamlit context
        def log_callback(log_msg):
            """Callback to display logs in real-time and store them"""
            status_container.write(log_msg)
            st.session_state.logs.append(log_msg)
        
        # Create logger with callback
        logger = CerberusMindLogger(callback=log_callback)
        
        # Pass logger through config (not serializable, so can't go in state)
        config = {
            "configurable": {
                "thread_id": st.session_state.thread_id,
                "logger": logger
            }
        }
        
        # Run Agent SYNCHRONOUSLY
        try:
            # Invoke the agent synchronously
            result = cerberus_agent.invoke(user_input, config=config)
            
            # Extract final response from result
            final_response = ""
            if "messages" in result:
                messages = result["messages"]
                # Get the last AI message
                for msg in reversed(messages):
                    if isinstance(msg, AIMessage):
                        final_response = msg.content
                        break
            
            # Update risk register if present
            if "risk_register" in result and result["risk_register"]:
                st.session_state.risk_register = result["risk_register"]
                logger.log("System", f"📊 Updated risk register: {len(result['risk_register'])} risks")
            
            # Display final response
            if final_response:
                response_placeholder.markdown(final_response)
                st.session_state.messages.append(AIMessage(content=final_response))
                status_container.update(label="✅ Cerberus Mind - Complete", state="complete")
                st.rerun()  # Rerun to update sidebar risk register
            else:
                response_placeholder.warning("Agent completed but no response was generated.")
                status_container.update(label="⚠️ Cerberus Mind - No Response", state="error")
                st.rerun()  # Rerun to update sidebar
                
        except NodeInterrupt as e:
            # The graph has paused for HITL!
            interrupt_value = str(e)
            st.session_state.awaiting_input = True
            st.session_state.interrupt_value = interrupt_value
            status_container.update(label="🛑 Awaiting Input", state="running")
            st.rerun()
            
        except Exception as e:
            st.error(f"Cerberus Crash: {e}")
            status_container.update(label="❌ Cerberus Mind - Error", state="error")