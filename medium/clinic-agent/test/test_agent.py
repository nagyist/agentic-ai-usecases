# test/test_agent.py - test agent
# Initialize state

from pathlib import Path
import sys

# Allow running this file directly: `python test/test_agent.py`.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from agents.booking_agent import create_initial_state, process_message


state = create_initial_state()

# Process messages
state = process_message(state, "Hi", thread_id="session_1")
print(state["messages"][-1]["content"])

state = process_message(state, "I want to book", thread_id="session_1")
print(state["available_options"])