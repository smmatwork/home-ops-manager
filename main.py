import os
from typing import Literal
from dotenv import load_dotenv

from langgraph.graph import StateGraph, START, END
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage

# Import our custom components
from state import HomeState
from hydrator import hydrate_household_context

load_dotenv()

# 1. Define the LLM Brain
# We use 'tools' to allow the agent to eventually write back to Supabase
llm = ChatAnthropic(model="claude-3-5-sonnet-20241022", temperature=0)

def call_brain(state: HomeState):
    """
    The reasoning node: Analyzes the household context and 
    decides if it needs to interview the user or create chores.
    """
    # Construct the 'Architect' System Prompt
    household_info = state.get("household", {})
    rooms = household_info.get("maintenance_notes", "No rooms defined")
    
    system_prompt = f"""
    You are the Home Operations Manager. 
    HOUSEHOLD CONTEXT: {rooms}
    
    YOUR GOAL:
    1. Check if you know the usage frequency (High/Medium/Low) for EVERY room listed above.
    2. IF usage info is missing: Ask the user specifically about those rooms.
    3. IF usage info is present: Acknowledge it and prepare to generate the cleaning schedule.
    
    Be concise, professional, and act as a senior project manager for the home.
    """
    
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    
    # In a production system, we would bind tools here
    # response = llm.bind_tools([create_bulk_chores]).invoke(messages)
    response = llm.invoke(messages)
    
    return {"messages": [response]}

# 2. Define the Routing Logic (Production Gatekeeper)
def should_continue(state: HomeState) -> Literal["continue", "end"]:
    """
    Decides if the conversation should end (waiting for user input)
    or move to tool execution.
    """
    messages = state['messages']
    last_message = messages[-1]
    
    # If the LLM wants to call a tool, we continue to the action node
    if last_message.tool_calls:
        return "continue"
    
    # Otherwise, we stop and wait for the user to reply to the interview questions
    return "end"

# 3. Build the Graph
workflow = StateGraph(HomeState)

# Add Nodes
workflow.add_node("hydrate", hydrate_household_context)
workflow.add_node("agent", call_brain)

# Define Flow
workflow.add_edge(START, "hydrate")
workflow.add_edge("hydrate", "agent")

# Add conditional routing
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": END, # We will add the 'action' node here later today
        "end": END
    }
)

# Compile the Graph
app = workflow.compile()
