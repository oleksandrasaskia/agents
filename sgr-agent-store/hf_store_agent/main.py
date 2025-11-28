import textwrap
from openai import OpenAI

# from store_agent import run_agent
from hf_store_agent import run_agent
from erc3 import ERC3

core = ERC3()
MODEL_ID = "gemini/gemini-2.0-flash-lite"

# Start session with metadata
res = core.start_session(
    benchmark="store", workspace="my", name="Simple HF Agent", architecture="HF Agent"
)

status = core.session_status(res.session_id)
print(f"Session has {len(status.tasks)} tasks")

for task in status.tasks:
    print("=" * 40)
    print(f"Starting Task: {task.task_id} ({task.spec_id}): {task.task_text}")
    # start the task
    core.start_task(task)

    try:
        run_agent(MODEL_ID, core, task)
    except Exception as e:
        print(e)
    result = core.complete_task(task)
    if result.eval:
        explain = textwrap.indent(result.eval.logs, "  ")
        print(f"\nSCORE: {result.eval.score}\n{explain}\n")
    break

core.submit_session(res.session_id)
