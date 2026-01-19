from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from .types import FetcherState, FetchStrategy
from .vdr_tools import execute_tool, tools_docs



llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)



def strategist_node(state: FetcherState):
    """
    Analyzes current data and decides next tool calls.
    """
    # Extract State
    instruction = state["instruction"]
    current_data_keys = list(state["fetched_data"].keys())
    iteration = state["iteration_count"]
    tool_logs = "\n".join(state["tool_logs"])
    fetched_data_summary = "\nFetched data summary:"
    max_cap_per_file = 1000 // (len(state["fetched_data"]) if len(state["fetched_data"]) > 0 else 1)
    for k, v in state['fetched_data'].items():
        fetched_data_summary += f"\n {k}: {v[:max_cap_per_file]}"
    
    # Broadcast Update
    print(f"[Data Fetcher] Strategising next steps ({iteration}/3)...")
    
    # System Prompt for Decision Making
    system_msg = f"""
    You are a Data Retrieval Strategist.
    Goal: "{instruction}"
    
    Decide the next set of tool calls to fetch missing info.
    - If you need to find files first, use 'filter_contracts' or 'filter_contracts_advanced'.
    - If you have files, read them ('read_file') or search ('search_clauses').
    - YOU MUSt ALWAYS USE FILENAMES WHEN CALLING TOOLS THAT REQUIRE THEM IF YOU HAVE THE FILENAMES. This will narrow DOWN the search and improve efficiency.
    - If no more data is needed, return an empty tool_calls list.
    - If you have the data, set is_complete=True.
    
    Here is the TOOLS DOCUMENTATION:
    {tools_docs}
    
    Already called tools and their logs:
    {tool_logs} 
    
    Fetched Data Summary:
    {fetched_data_summary}
    """
    
    # Invoke LLM with Structured Output
    structured_llm = llm.with_structured_output(FetchStrategy)
    strategy = structured_llm.invoke([
        SystemMessage(content=system_msg),
        HumanMessage(content="What is the next step?")
    ])
    
    return {
        "pending_tool_calls": [t.model_dump() for t in strategy.tool_calls],
        "final_summary": strategy.reasoning if strategy.is_complete else ""
    }
    

    
def executor_node(state: FetcherState):
    """
    Executes the list of pending tools and updates state.
    """
    tool_calls = state["pending_tool_calls"]
    new_data = {}
    new_logs = []
    
    for call in tool_calls:
        tool_name = call["tool_name"]
        args = {arg["name"]: arg["value"] for arg in call["arguments"]}
        save_key = call["output_key"]
        
        # Broadcast Update
        print(f"[Data Fetcher] Executing tool: {tool_name} with args: {args}")
        
        # Execute (This would be async in production)
        try:
            result = execute_tool(tool_name, args)
            
            # Save to KV pair
            new_data[save_key] = result['data']
            new_logs.append(f"✅ Ran {tool_name} with args: {args}: Saved to '{save_key}'. tool run message: {result['message']}")
            
        except Exception as e:
            new_logs.append(f"❌ Error running {tool_name} with args: {args}: {str(e)}")
            new_data[save_key] = "Error fetching data"

    # Merge new data into existing fetched_data
    updated_db = {**state["fetched_data"], **new_data}
    
    return {
        "fetched_data": updated_db,
        "tool_logs": state["tool_logs"] + new_logs,
        "iteration_count": state["iteration_count"] + 1,
        "pending_tool_calls": [] # Clear queue
    }


def forced_ending_node(state: FetcherState):
    """
    Generates a summary when max iterations are reached.
    """
    instruction = state["instruction"]
    fetched_data = state["fetched_data"]
    iteration = state["iteration_count"]
    tool_logs = state["tool_logs"]
    
    # Broadcast Update
    print(f"[Data Fetcher] Max iterations reached ({iteration}). Generating forced summary...")
    
    # System Prompt for Summary Generation
    system_msg = f"""
    You are a Data Retrieval Analyst.
    Original Goal: "{instruction}"
    
    The maximum iteration limit has been reached.
    Summarize what data was successfully retrieved and what is still missing.
    
    Available Data Keys: {list(fetched_data.keys())}
    Tool Execution Logs: {tool_logs}
    
    Provide a concise summary of:
    1. What was successfully retrieved
    2. What is still missing or incomplete
    """
    
    # Invoke LLM for summary
    response = llm.invoke([
        SystemMessage(content=system_msg),
        HumanMessage(content="Provide a summary of the data retrieval process.")
    ])
    
    summary = response.content
    
    return {
        "final_summary": f"⚠️ Max iterations reached.\n\n{summary}"
    }