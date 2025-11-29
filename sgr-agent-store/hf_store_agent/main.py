import textwrap
from openai import OpenAI
import os

from hf_store_agent import run_agent
from erc3 import ERC3

from usage_tracking_model import UsageTrackingModel

core = ERC3()

usage_tracking_model = UsageTrackingModel(
    model_id="gemini/gemini-2.0-flash-lite", api_key=os.getenv("GEMINI_API_KEY")
)

usage_tracking_model = UsageTrackingModel(
    model_id="gpt-5-mini", api_key=os.getenv("OPENAI_API_KEY")
)

# Start session with metadata
res = core.start_session(
    benchmark="store",
    workspace="my",
    name="Store Agent gpt-5-mini",
    architecture="Coding Agent",
)

status = core.session_status(res.session_id)
print(f"Session has {len(status.tasks)} tasks")

for i, task in enumerate(status.tasks):
    print("=" * 40)
    print(f"Starting Task {i}: {task.task_id} ({task.spec_id}): {task.task_text}")
    # start the task
    core.start_task(task)

    try:
        run_agent(usage_tracking_model, core, task)
    except Exception as e:
        print(e)
    result = core.complete_task(task)
    if result.eval:
        explain = textwrap.indent(result.eval.logs, "  ")
        print(f"\nSCORE: {result.eval.score}\n{explain}\n")

    if i == 2:  # Limit to first 4 tasks for demo purposes
        break

core.submit_session(res.session_id)
