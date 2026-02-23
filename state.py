from typing import Annotated, TypedDict, List, Dict, Any
from langgraph.graph.message import add_messages

class HomeState(TypedDict):
    # 1. Conversation Memory
    # 'add_messages' ensures new messages are appended rather than overwriting the old ones
    messages: Annotated[List[Any], add_messages]
    
    # 2. Database Context (Hydrated from Supabase)
    user_id: int
    household: Dict[str, Any]  # Details about the house (rooms, etc.)
    users: List[Dict[str, Any]] # All residents
    helpers: List[Dict[str, Any]] # Maid, Cook, etc.
    
    # 3. Reasoning State
    # This helps the agent keep track of its plan
    missing_info: List[str] # e.g., ["usage_frequency_guest_room"]
