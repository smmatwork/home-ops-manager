from main import app

# Simulate the user asking for a schedule
inputs = {
    "user_id": 1,  # Matches your Supabase ID
    "messages": [("user", "I want to set up a cleaning schedule for the whole house.")]
}

# Use stream_mode="updates" so each chunk is {node_name: state_update}
for output in app.stream(
    inputs, config={"configurable": {"thread_id": "1"}}, stream_mode="updates"
):
    for node_name, value in output.items():
        print(f"--- Node: {node_name} ---")
        if "messages" in value and value["messages"]:
            last_msg = value["messages"][-1]
            content = getattr(last_msg, "content", str(last_msg))
            print(content)
