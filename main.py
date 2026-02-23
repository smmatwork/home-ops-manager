import os
from typing import Literal
from dotenv import load_dotenv

from langgraph.graph import StateGraph, START, END
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage

# Import our custom components
from state import HomeState
from hydrator import hydrate_household_context, check_limits, check_message_limit
from limits import MAX_USERS_PER_HOUSEHOLD, MAX_HELPERS_PER_HOUSEHOLD, MAX_MONTHLY_MESSAGES_FREE, MAX_MONTHLY_MESSAGES_PRO

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

    at_user_limit = state.get("at_user_limit", False)
    at_helper_limit = state.get("at_helper_limit", False)
    at_message_limit = state.get("at_message_limit", False)
    subscription_tier = state.get("subscription_tier", "free")
    monthly_message_count = state.get("monthly_message_count", 0)

    message_limit = MAX_MONTHLY_MESSAGES_PRO if subscription_tier == "pro" else MAX_MONTHLY_MESSAGES_FREE

    limit_notes = []
    if at_user_limit:
        limit_notes.append(
            f"The household has reached the maximum of {MAX_USERS_PER_HOUSEHOLD} family members."
        )
    if at_helper_limit:
        limit_notes.append(
            f"The household has reached the maximum of {MAX_HELPERS_PER_HOUSEHOLD} home helpers."
        )
    if at_message_limit:
        limit_notes.append(
            f"The user has reached their monthly chat message limit of {message_limit} messages "
            f"('{subscription_tier}' tier). They must upgrade or wait until next month to continue chatting."
        )
    limit_section = (
        "LIMIT ALERTS:\n" + "\n".join(f"- {n}" for n in limit_notes)
        if limit_notes
        else "No limits reached."
    )

    system_prompt = f"""
    You are the Home Operations Manager. 
    HOUSEHOLD CONTEXT: {rooms}

    SUBSCRIPTION: {subscription_tier.upper()} tier — {monthly_message_count}/{message_limit} messages used this month.

    {limit_section}
    
    YOUR GOAL:
    1. Check if you know the usage frequency (High/Medium/Low) for EVERY room listed above.
    2. IF usage info is missing: Ask the user specifically about those rooms.
    3. IF usage info is present: Acknowledge it and prepare to generate the cleaning schedule.
    4. If any household limit has been reached, inform the user clearly.
    5. If the monthly message limit has been reached, tell the user they must upgrade their plan or wait until next month.
    
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
workflow.add_node("check_limits", check_limits)
workflow.add_node("check_message_limit", check_message_limit)
workflow.add_node("agent", call_brain)

# Define Flow
workflow.add_edge(START, "hydrate")
workflow.add_edge("hydrate", "check_limits")
workflow.add_edge("check_limits", "check_message_limit")
workflow.add_edge("check_message_limit", "agent")

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
