import os
from typing import Dict, Any
from supabase import create_client, Client
from dotenv import load_dotenv

from state import HomeState

# 1. Setup Connection
load_dotenv()
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(url, key)

# hydrator.py
def hydrate_household_context(state: HomeState):
    user_id = state.get("user_id")
    
    # 1. Fetch User and their Household ID
    user_data = supabase.table("users").select("*, household(*)").eq("id", user_id).single().execute()
    
    if not user_data.data:
        return {"error": "User not found"}
    
    h_id = user_data.data['household_id']
    
    # 2. Parallel Fetch for Efficiency
    # Fetch all users and helpers for this specific household
    users_in_house = supabase.table("users").select("*").eq("household_id", h_id).execute()
    helpers_in_house = supabase.table("home_help").select("*").eq("household_id", h_id).execute()
    
    return {
        "household": user_data.data['household'],
        "users": users_in_house.data,
        "helpers": helpers_in_house.data,
    }
