from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain.agents.structured_output import ToolStrategy

from .types import FetchedData
from .vdr_tools import vdr_tools
from .prompt import DATA_FETCHER_SYSTEM_PROMPT


    
llm = ChatOpenAI(
    model="gpt-4.1",
    streaming=True,  # token streaming works here
)
data_fetcher_agent = create_agent(
    model=llm,
    tools=vdr_tools,
    system_prompt=DATA_FETCHER_SYSTEM_PROMPT,
    response_format=ToolStrategy(FetchedData),
)


def data_fetcher_node(instruction: str) -> dict:
    """
    Executes the Data Fetcher ReAct Agent for the given instruction.
    """
    # 1. Broadcast Update
    print(f"[Node] Data Fetcher Invoked with instruction: {instruction}")
    
    # 2. Run the ReAct Agent Loop with streaming
    inputs = {"messages": [HumanMessage(content=instruction)]}
    
    input_tokens_used = 0
    output_tokens_used = 0
    call_data = []
    for chunk in data_fetcher_agent.stream(inputs, stream_mode="updates"): 
        for step, data in chunk.items():
            print(f"[Node][Data Fetcher] >> step: {step}")
            #print(f"content: {data['messages'][-1].content_blocks}")
            if step == 'model':
                input_tokens_used += sum([aimessage.usage_metadata['input_tokens'] for aimessage in data['messages'] if isinstance(aimessage, AIMessage)])
                output_tokens_used += sum([aimessage.usage_metadata['output_tokens'] for aimessage in data['messages'] if isinstance(aimessage, AIMessage)])
                for content in data['messages'][-1].content_blocks:
                    if content['type'] == 'tool_call':
                        print(f"[Node][Data Fetcher] >> Calling TOOL: {content['name']} with args {content['args']}")
                    elif content['type'] == 'text':
                        print(f"[Node][Data Fetcher] >> {content['text']}")
                    else:
                        print(f"[Node][Data Fetcher] >> Unknown content type: {content}")
            if step == 'tools':
                print(f"[Node][Data Fetcher] >> TOOL RESULT: {data['messages'][-1].content_blocks}")
            call_data.append(data['messages'][-1].content_blocks)
    
    # 3. Extract Final Response
    final_response: FetchedData = chunk['model']['structured_response']
    
    # 4. Log and Return
    log_msg = (
        f"📥 Data Fetcher: Fetched {len(final_response.data)} items. "
        f"[Tokens: In={input_tokens_used}, Out={output_tokens_used}]"
    )
    
    return {
        "fetched_data": final_response,
        "logs": [log_msg],
        "call_data": call_data
    }