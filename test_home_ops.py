import os
from dotenv import load_dotenv
from hydrator import hydrate_household_context, check_limits, check_message_limit
from limits import MAX_USERS_PER_HOUSEHOLD, MAX_HELPERS_PER_HOUSEHOLD, MAX_MONTHLY_MESSAGES_FREE, MAX_MONTHLY_MESSAGES_PRO

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

    # --- Check 4: Monthly Message Limit Logic ---
    print("\n💬 Running monthly message limit checks...")

    # Scenario E: Free tier, under the limit
    state_free_under = {
        "household": {"subscription_tier": "free"},
        "monthly_message_count": MAX_MONTHLY_MESSAGES_FREE - 1,
    }
    result_e = check_message_limit(state_free_under)
    assert result_e["subscription_tier"] == "free", "Expected subscription_tier='free'"
    assert result_e["at_message_limit"] is False, "Expected at_message_limit=False when free user is under limit"
    print("✅ Free tier under-limit scenario passed.")

    # Scenario F: Free tier, exactly at the limit
    state_free_at = {
        "household": {"subscription_tier": "free"},
        "monthly_message_count": MAX_MONTHLY_MESSAGES_FREE,
    }
    result_f = check_message_limit(state_free_at)
    assert result_f["at_message_limit"] is True, "Expected at_message_limit=True when free user is at limit"
    print("✅ Free tier at-limit scenario passed.")

    # Scenario G: Pro tier, above the free limit but under the pro limit
    state_pro_mid = {
        "household": {"subscription_tier": "pro"},
        "monthly_message_count": MAX_MONTHLY_MESSAGES_FREE + 10,
    }
    result_g = check_message_limit(state_pro_mid)
    assert result_g["subscription_tier"] == "pro", "Expected subscription_tier='pro'"
    assert result_g["at_message_limit"] is False, "Expected at_message_limit=False for pro user above free limit but below pro limit"
    print("✅ Pro tier mid-range scenario passed.")

    # Scenario H: Pro tier, exactly at the pro limit
    state_pro_at = {
        "household": {"subscription_tier": "pro"},
        "monthly_message_count": MAX_MONTHLY_MESSAGES_PRO,
    }
    result_h = check_message_limit(state_pro_at)
    assert result_h["at_message_limit"] is True, "Expected at_message_limit=True when pro user is at the pro limit"
    print("✅ Pro tier at-limit scenario passed.")

    # Scenario I: No subscription_tier in household (defaults to free)
    state_default_tier = {
        "household": {},
        "monthly_message_count": MAX_MONTHLY_MESSAGES_FREE - 1,
    }
    result_i = check_message_limit(state_default_tier)
    assert result_i["subscription_tier"] == "free", "Expected subscription_tier to default to 'free'"
    assert result_i["at_message_limit"] is False, "Expected at_message_limit=False for default tier under limit"
    print("✅ Default tier (no subscription_tier key) scenario passed.")

    # Scenario J: Zero messages sent
    state_zero = {
        "household": {"subscription_tier": "free"},
        "monthly_message_count": 0,
    }
    result_j = check_message_limit(state_zero)
    assert result_j["at_message_limit"] is False, "Expected at_message_limit=False when no messages sent"
    print("✅ Zero messages scenario passed.")

    print("\n🎉 All monthly message limit tests passed!")


if __name__ == "__main__":
    run_test()
