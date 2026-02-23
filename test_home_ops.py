import os
from dotenv import load_dotenv
from hydrator import hydrate_household_context

# 1. Load Environment
load_dotenv()

def run_test():
    print("🚀 Starting Day 1 Integration Test...")

    # --- Check 1: Environment Variables ---
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
        print("❌ Error: Supabase credentials missing from .env file.")
        return

    # --- Check 2: Hydration Logic ---
    # We are simulating a starting state with User ID 1 (ensure ID 1 exists in your DB!)
    mock_state = {
        "user_id": 1,
        "messages": []
    }

    try:
        print("📡 Connecting to Supabase and hydrating state...")
        final_state = hydrate_household_context(mock_state)

        if "users" in final_state and len(final_state["users"]) > 0:
            user = final_state["users"][0]
            print("✅ SUCCESS! Data retrieved from Postgres.")
            print(f"👤 User Found: {user.get('name')}")
            print(f"🎯 Current Goal: {user.get('goals')}")
            print(f"🥗 Diet: {user.get('diet_restrictions')}")
        else:
            print("⚠️ Connection worked, but no user was found with ID 1.")
            print("Action: Check your Supabase Table Editor and ensure a user exists with id=1.")

    except Exception as e:
        print(f"❌ Critical Failure: {str(e)}")

if __name__ == "__main__":
    run_test()
