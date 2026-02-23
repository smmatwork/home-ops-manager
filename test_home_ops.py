import os
from dotenv import load_dotenv
from hydrator import hydrate_household_context, check_limits
from limits import MAX_USERS_PER_HOUSEHOLD, MAX_HELPERS_PER_HOUSEHOLD

# 1. Load Environment
load_dotenv()


def run_test():
    print("🚀 Starting Integration Test...")

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
        return

    # --- Check 3: Limit Evaluation Logic ---
    print("\n🔍 Running limit checks...")

    # Scenario A: Under the limits
    state_under_limit = {
        "users": [{"id": i} for i in range(MAX_USERS_PER_HOUSEHOLD - 1)],
        "helpers": [{"id": i} for i in range(MAX_HELPERS_PER_HOUSEHOLD - 1)],
    }
    result_a = check_limits(state_under_limit)
    assert result_a["at_user_limit"] is False, "Expected at_user_limit=False when under the user limit"
    assert result_a["at_helper_limit"] is False, "Expected at_helper_limit=False when under the helper limit"
    print("✅ Under-limit scenario passed.")

    # Scenario B: Exactly at the limits
    state_at_limit = {
        "users": [{"id": i} for i in range(MAX_USERS_PER_HOUSEHOLD)],
        "helpers": [{"id": i} for i in range(MAX_HELPERS_PER_HOUSEHOLD)],
    }
    result_b = check_limits(state_at_limit)
    assert result_b["at_user_limit"] is True, "Expected at_user_limit=True when at the user limit"
    assert result_b["at_helper_limit"] is True, "Expected at_helper_limit=True when at the helper limit"
    print("✅ At-limit scenario passed.")

    # Scenario C: Over the limits
    state_over_limit = {
        "users": [{"id": i} for i in range(MAX_USERS_PER_HOUSEHOLD + 2)],
        "helpers": [{"id": i} for i in range(MAX_HELPERS_PER_HOUSEHOLD + 2)],
    }
    result_c = check_limits(state_over_limit)
    assert result_c["at_user_limit"] is True, "Expected at_user_limit=True when over the user limit"
    assert result_c["at_helper_limit"] is True, "Expected at_helper_limit=True when over the helper limit"
    print("✅ Over-limit scenario passed.")

    # Scenario D: Empty household
    state_empty = {"users": [], "helpers": []}
    result_d = check_limits(state_empty)
    assert result_d["at_user_limit"] is False, "Expected at_user_limit=False for empty household"
    assert result_d["at_helper_limit"] is False, "Expected at_helper_limit=False for empty household"
    print("✅ Empty-household scenario passed.")

    print("\n🎉 All limit-check tests passed!")


if __name__ == "__main__":
    run_test()
