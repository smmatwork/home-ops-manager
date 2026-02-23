import os
from typing import Dict, Any
from supabase import create_client, Client
from dotenv import load_dotenv

from state import HomeState
from limits import MAX_USERS_PER_HOUSEHOLD, MAX_HELPERS_PER_HOUSEHOLD, MAX_MONTHLY_MESSAGES_FREE, MAX_MONTHLY_MESSAGES_PRO

# 1. Setup Connection
load_dotenv()
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(url, key)

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


def check_limits(state: HomeState):
    """Evaluate whether the household has reached its user or helper limits."""
    users = state.get("users") or []
    helpers = state.get("helpers") or []

    return {
        "at_user_limit": len(users) >= MAX_USERS_PER_HOUSEHOLD,
        "at_helper_limit": len(helpers) >= MAX_HELPERS_PER_HOUSEHOLD,
    }


def check_message_limit(state: HomeState):
    """Evaluate whether the household has reached its monthly chat message limit."""
    household = state.get("household") or {}
    subscription_tier = household.get("subscription_tier", "free")

    monthly_message_count = state.get("monthly_message_count", 0)

    if subscription_tier == "pro":
        limit = MAX_MONTHLY_MESSAGES_PRO
    else:
        limit = MAX_MONTHLY_MESSAGES_FREE

    return {
        "subscription_tier": subscription_tier,
        "at_message_limit": monthly_message_count >= limit,
    }
