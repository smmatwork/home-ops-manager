import streamlit as st
import os
from supabase import create_client
from dotenv import load_dotenv
from main import app as agent_app # Your LangGraph engine
from limits import MAX_USERS_PER_HOUSEHOLD, MAX_HELPERS_PER_HOUSEHOLD, MAX_MONTHLY_MESSAGES_FREE, MAX_MONTHLY_MESSAGES_PRO

load_dotenv()

# 1. Production-Grade Connection Pooling
@st.cache_resource
def init_connection():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not url.startswith(("http://", "https://")):
        raise ValueError(
            "Missing/invalid SUPABASE_URL. Set SUPABASE_URL to your Supabase project URL (https://...)."
        )
    if not key:
        raise ValueError(
            "Missing SUPABASE_SERVICE_ROLE_KEY. Set it in your .env (keep it private; never commit)."
        )
    return create_client(url, key)

try:
    supabase = init_connection()
except Exception as e:
    st.set_page_config(page_title="HomeOps Admin", layout="wide")
    st.title("🏡 Home Operations Manager")
    st.error("Supabase connection is not configured or not reachable.")
    st.code(str(e))
    st.stop()

# 2. Page Configuration
st.set_page_config(page_title="HomeOps Admin", layout="wide")
st.title("🏡 Home Operations Manager")

# 3. Persistent Session State (Crucial for Production)
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_id" not in st.session_state:
    st.session_state.user_id = 1 # Default for Day 2
if "monthly_message_count" not in st.session_state:
    st.session_state.monthly_message_count = 0
if "subscription_tier" not in st.session_state:
    st.session_state.subscription_tier = "free"

# --- UI LAYOUT ---
tab1, tab2, tab3 = st.tabs(["Dashboard", "Inventory & Help", "Agent Chat"])

with tab1:
    st.header("Household Configuration")
    # Fetch current house data
    try:
        house = supabase.table("household").select("*").eq("id", 1).single().execute()
    except Exception as e:
        st.error("Failed to load household row from Supabase.")
        st.code(str(e))
        st.stop()
    
    with st.form("house_form"):
        desc = st.text_input("House Description", value=house.data.get('description') if house.data else "")
        rooms = st.text_area("Room Inventory (comma separated)", value=house.data.get('maintenance_notes') if house.data else "")
        if st.form_submit_button("Update House"):
            supabase.table("household").upsert({"id": 1, "description": desc, "maintenance_notes": rooms}).execute()
            st.success("House updated!")

with tab2:
    col1, col2 = st.columns(2)
    
    # --- COLUMN 1: FAMILY MEMBERS ---
    with col1:
        st.subheader("👨‍👩‍👧‍👦 Family Members")

        # Fetch current users to check limit
        users_df = supabase.table("users").select("name, diet_restrictions, goals").eq("household_id", 1).execute()
        current_user_count = len(users_df.data) if users_df.data else 0
        at_user_limit = current_user_count >= MAX_USERS_PER_HOUSEHOLD

        if at_user_limit:
            st.warning(
                f"⚠️ Limit reached: This household already has {current_user_count} family members "
                f"(maximum is {MAX_USERS_PER_HOUSEHOLD}). Remove a member before adding a new one."
            )
        
        # Form to add a new user — disabled when the limit is reached
        with st.form("add_user_form", clear_on_submit=True):
            new_name = st.text_input("Name", disabled=at_user_limit)
            new_diet = st.selectbox("Diet Preference", ["Punjabi Veg", "Non-Veg", "Vegan", "Keto"], disabled=at_user_limit)
            new_goal = st.text_input("Health Goal", "Weight reduction", disabled=at_user_limit)
            if st.form_submit_button("Add Family Member", disabled=at_user_limit):
                supabase.table("users").insert({
                    "name": new_name, 
                    "diet_restrictions": new_diet, 
                    "goals": new_goal,
                    "household_id": 1
                }).execute()
                st.success(f"Added {new_name}!")
                st.rerun()

        # DISPLAY: Show current users
        if users_df.data:
            st.table(users_df.data)
        else:
            st.info("No family members added yet.")

    # --- COLUMN 2: HOME HELPERS ---
    with col2:
        st.subheader("🧹 Home Helpers")

        # Fetch current helpers to check limit
        helpers_df = supabase.table("home_help").select("name, role, schedule_config").eq("household_id", 1).execute()
        current_helper_count = len(helpers_df.data) if helpers_df.data else 0
        at_helper_limit = current_helper_count >= MAX_HELPERS_PER_HOUSEHOLD

        if at_helper_limit:
            st.warning(
                f"⚠️ Limit reached: This household already has {current_helper_count} home helpers "
                f"(maximum is {MAX_HELPERS_PER_HOUSEHOLD}). Remove a helper before adding a new one."
            )
        
        # Form to add a new helper — disabled when the limit is reached
        with st.form("add_helper_form", clear_on_submit=True):
            h_name = st.text_input("Name", disabled=at_helper_limit)
            h_role = st.selectbox("Role", ["Maid", "Cook", "Driver", "Gardener", "Nanny"], disabled=at_helper_limit)
            
            # New Structured Schedule Fields
            h_days = st.multiselect(
                "Work Days", 
                ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                default=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                disabled=at_helper_limit
            )
            
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                start_time = st.time_input("Start Time", value=None, disabled=at_helper_limit)
            with col_t2:
                end_time = st.time_input("End Time", value=None, disabled=at_helper_limit)
                
            if st.form_submit_button("Add Helper", disabled=at_helper_limit):
                # Combine days and time into a single string or JSON for the DB
                schedule_str = f"{', '.join(h_days)} | {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"
                
                supabase.table("home_help").insert({
                    "name": h_name, 
                    "role": h_role, 
                    "schedule_config": schedule_str, # Storing as a readable string
                    "household_id": 1
                }).execute()
                st.success(f"Added {h_name}!")
                st.rerun()

        # DISPLAY: Updated Table
        if helpers_df.data:
            # We use a dataframe display for better horizontal scrolling of the schedule
            st.dataframe(helpers_df.data, use_container_width=True)

with tab3:
    st.header("Agent Interview")

    # --- Subscription & Message Limit Status ---
    subscription_tier = st.session_state.subscription_tier
    monthly_message_count = st.session_state.monthly_message_count
    monthly_limit = MAX_MONTHLY_MESSAGES_PRO if subscription_tier == "pro" else MAX_MONTHLY_MESSAGES_FREE
    at_message_limit = monthly_message_count >= monthly_limit
    messages_remaining = max(0, monthly_limit - monthly_message_count)

    tier_label = "⭐ Pro" if subscription_tier == "pro" else "Free"
    st.caption(
        f"Plan: **{tier_label}** — {monthly_message_count}/{monthly_limit} messages used this month "
        f"({messages_remaining} remaining)"
    )
    st.progress(min(monthly_message_count / monthly_limit, 1.0))

    if at_message_limit:
        st.error(
            f"🚫 Monthly limit reached: You have used all {monthly_limit} messages included in your "
            f"**{subscription_tier}** plan. "
            + ("Please wait until next month to continue." if subscription_tier == "pro"
               else f"Upgrade to **Pro** for up to {MAX_MONTHLY_MESSAGES_PRO} messages/month.")
        )
    else:
        st.info("The agent will interview you about room usage here.")

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat Input — disabled when the monthly limit is reached
    if not at_message_limit:
        if prompt := st.chat_input("Ask about the cleaning schedule..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.monthly_message_count += 1
            with st.chat_message("user"):
                st.markdown(prompt)

            # TRIGGER THE LANGGRAPH AGENT
            with st.chat_message("assistant"):
                inputs = {
                    "user_id": st.session_state.user_id,
                    "messages": [("user", prompt)],
                    "monthly_message_count": st.session_state.monthly_message_count,
                }
                # Stream the response from your LangGraph main.py
                response_text = ""
                for output in agent_app.stream(inputs, config={"configurable": {"thread_id": "1"}}):
                    for key, value in output.items():
                        if key == "agent":
                            response_text = value["messages"][-1].content
                
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
    else:
        st.chat_input("Monthly message limit reached — chat disabled.", disabled=True)
