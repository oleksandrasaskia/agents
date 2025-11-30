# uv run main.py --model gpt-4o
# uv run main.py --model gpt-5-mini
# uv run main.py --model gemini
# uv run main.py --model gpt-5-mini --yaml system_prompt_minimal_gpt5-mini.yaml
# uv run main.py --model gemini --yaml system_prompt_minimal_gemini.yaml

import textwrap
import os
import argparse

from hf_store_agent import run_agent
from erc3 import ERC3

from usage_tracking_model import UsageTrackingModel

# Parse command-line arguments
parser = argparse.ArgumentParser(
    description="Run the store agent with different models"
)
parser.add_argument(
    "--model",
    type=str,
    choices=["gpt-5-mini", "gemini"],
    default="gpt-5-mini",
    help="Model to use: gpt-5-mini, or gemini",
)
parser.add_argument(
    "--yaml",
    type=str,
    default="system_prompt_minimal.yaml",
    help="YAML file name for system prompt (e.g., system_prompt_minimal.yaml)",
)
args = parser.parse_args()

core = ERC3()

# usage_tracking_model = UsageTrackingModel(
#   model_id="gemini/gemini-2.0-flash-lite", api_key=os.getenv("GEMINI_API_KEY")
# )

# usage_tracking_model = UsageTrackingModel(
#    model_name_for_logging="openai/gpt-5-mini",
#    model_id="gpt-5-mini",
#    api_key=os.getenv("OPENAI_API_KEY"),
# )

# Initialize model based on argument
if args.model == "gpt-5-mini":
    usage_tracking_model = UsageTrackingModel(
        model_name_for_logging="openai/gpt-5-mini",
        model_id="gpt-5-mini",
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    agent_name = "Store Agent gpt-5-mini"
elif args.model == "gemini":
    usage_tracking_model = UsageTrackingModel(
        model_id="gemini/gemini-2.0-flash-lite", api_key=os.getenv("GEMINI_API_KEY")
    )
    agent_name = "Store Agent gemini"

# Set workspace name including yaml filename
yaml_filename = args.yaml
workspace_name = f"{args.model} - {yaml_filename}"

# Start session with metadata
res = core.start_session(
    benchmark="store",
    workspace=workspace_name,
    name=agent_name,
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
        run_agent(usage_tracking_model, core, task, workspace_name, yaml_filename)
    except Exception as e:
        print(e)
    result = core.complete_task(task)
    if result.eval:
        explain = textwrap.indent(result.eval.logs, "  ")
        print(f"\nSCORE: {result.eval.score}\n{explain}\n")


core.submit_session(res.session_id)
