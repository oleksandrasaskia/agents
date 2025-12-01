import time
import logging
import os
import yaml
from pathlib import Path
from erc3 import TaskInfo, ERC3
from smolagents import (
    CodeAgent,
    PromptTemplates,
    PlanningPromptTemplate,
    ManagedAgentPromptTemplate,
    FinalAnswerPromptTemplate,
)
from usage_tracking_model import UsageTrackingModel

from agent_dev_tools import (
    FinalAnswerTool,
    GetCustomerTool,
    GetEmployeeTool,
    GetProjectTool,
    GetTimeEntryTool,
    ListCustomersTool,
    ListEmployeesTool,
    ListProjectsTool,
    ListWikiTool,
    LoadWikiTool,
    LogTimeEntryTool,
    ProvideAgentResponseTool,
    SearchCustomersTool,
    SearchEmployeesTool,
    SearchProjectsTool,
    SearchTimeEntriesTool,
    SearchWikiTool,
    TimeSummaryByEmployeeTool,
    TimeSummaryByProjectTool,
    UpdateEmployeeInfoTool,
    UpdateProjectStatusTool,
    UpdateProjectTeamTool,
    UpdateTimeEntryTool,
    UpdateWikiTool,
    WhoAmITool,
)

CLI_RED = "\x1b[31m"
CLI_GREEN = "\x1b[32m"
CLI_CLR = "\x1b[0m"


# Load system prompt from YAML file
def load_system_prompt_from_yaml(yaml_filename="system_prompt_minimal.yaml"):
    """Load system prompt from a YAML file in the same directory as this script."""
    current_dir = Path(__file__).parent
    yaml_path = current_dir / yaml_filename

    with open(yaml_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        print(f"== Loaded system prompt from {yaml_filename}")

    return config.get("system_prompt", "")


def create_prompt_templates(system_prompt):
    """Create prompt templates with the given system prompt."""
    return PromptTemplates(
        system_prompt=system_prompt,
        planning=PlanningPromptTemplate(
            initial_plan="",
            update_plan_pre_messages="",
            update_plan_post_messages="",
        ),
        managed_agent=ManagedAgentPromptTemplate(task="", report=""),
        final_answer=FinalAnswerPromptTemplate(pre_messages="", post_messages=""),
    )


def run_agent(
    usage_tracking_model: UsageTrackingModel,
    api: ERC3,
    task: TaskInfo,
    workspace_name: str,
    yaml_filename: str = "system_prompt_minimal.yaml",
):
    # Load system prompt from specified YAML file
    system_prompt = load_system_prompt_from_yaml(yaml_filename)
    prompt_templates = create_prompt_templates(system_prompt)

    # Setup logging with both file and console output
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_filename = (
        f"logs/{timestamp}/agent_run_{workspace_name}_{task.task_id}.log"
    )
    # Ensure the log directory exists before configuring logging
    log_dir = os.path.dirname(log_filename)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    
    # Remove existing handlers to ensure fresh logging setup for each task
    logger = logging.getLogger()
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
    
    # Configure fresh logging for this task
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_filename, mode="w", encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,  # Force reconfiguration
    )

    # Enable DEBUG logging for smolagents to see full reasoning/thinking
    logging.getLogger("smolagents").setLevel(logging.DEBUG)

    logging.info(f"{CLI_GREEN}[INIT]{CLI_CLR} Starting agent for task: {task.task_id}")
    logging.info(f"{CLI_GREEN}[TASK]{CLI_CLR} {task.task_text}")
    logging.info(f"Agent started for task {task.task_id}: {task.task_text}")

    store_api = api.get_erc_dev_client(task)
    about = store_api.who_am_i()

    # Create all the tools for the agent
    logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} About to create tools...")
    tools = []

    try:
        logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating FinalAnswerTool...")
        tools.append(FinalAnswerTool())
        logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating GetCustomerTool...")
        tools.append(GetCustomerTool(store_api))
        logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating GetEmployeeTool...")
        tools.append(GetEmployeeTool(store_api))
        logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating GetProjectTool...")
        tools.append(GetProjectTool(store_api))
        logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating GetTimeEntryTool...")
        tools.append(GetTimeEntryTool(store_api))
        logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating ListCustomersTool...")
        tools.append(ListCustomersTool(store_api))
        logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating ListEmployeesTool...")
        tools.append(ListEmployeesTool(store_api))
        logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating ListProjectsTool...")
        tools.append(ListProjectsTool(store_api))
        logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating ListWikiTool...")
        tools.append(ListWikiTool(store_api))
        logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating LoadWikiTool...")
        tools.append(LoadWikiTool(store_api))
        logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating LogTimeEntryTool...")
        tools.append(LogTimeEntryTool(store_api))
        logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating ProvideAgentResponseTool...")
        tools.append(ProvideAgentResponseTool(store_api))
        logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating SearchCustomersTool...")
        tools.append(SearchCustomersTool(store_api))
        logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating SearchEmployeesTool...")
        tools.append(SearchEmployeesTool(store_api))
        logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating SearchProjectsTool...")
        tools.append(SearchProjectsTool(store_api))
        logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating SearchTimeEntriesTool...")
        tools.append(SearchTimeEntriesTool(store_api))
        logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating SearchWikiTool...")
        tools.append(SearchWikiTool(store_api))
        logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating TimeSummaryByEmployeeTool...")
        tools.append(TimeSummaryByEmployeeTool(store_api))
        logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating TimeSummaryByProjectTool...")
        tools.append(TimeSummaryByProjectTool(store_api))
        logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating UpdateEmployeeInfoTool...")
        tools.append(UpdateEmployeeInfoTool(store_api))
        logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating UpdateProjectStatusTool...")
        tools.append(UpdateProjectStatusTool(store_api))
        logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating UpdateProjectTeamTool...")
        tools.append(UpdateProjectTeamTool(store_api))
        logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating UpdateTimeEntryTool...")
        tools.append(UpdateTimeEntryTool(store_api))
        logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating UpdateWikiTool...")
        tools.append(UpdateWikiTool(store_api))
        logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating WhoAmITool...")
        tools.append(WhoAmITool(store_api))
        logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} All tools created successfully")
    except Exception as e:
        logging.info(
            f"{CLI_RED}[ERROR]{CLI_CLR} Failed to create tools: {type(e).__name__}: {e}"
        )
        import traceback

        logging.info(f"{CLI_RED}[TRACEBACK]{CLI_CLR}")
        traceback.print_exc()
        raise

    logging.info(
        f"{CLI_GREEN}[TOOLS]{CLI_CLR} Loaded {len(tools)} tools: {[tool.name for tool in tools]}"
    )
    logging.info(f"Tools initialized: {[tool.name for tool in tools]}")

    instructions = f"""
You are AI business assistant for the company. You are helping with tasks related to project management, time tracking, and employee management.
Knowledge:
- Use the company wiki API (especially `rulebook.md`) and related internal data for policies and backstory.

Access control:
- Enforce the current user's access strictly:
    - Executives: broad access.
    - Project leads: write access for projects they lead.
    - Team members: read-only.
    - Guests (no account), ppublic users: public-safe data only; refuse sensitive requests and never reveal internal identities; log a denied_security response if needed.

Response requirements:
- Always include a clear outcome status.
- Include explicit entity links unless access control forbids them.

Operational rules:
- To confirm project access: first search/find the project, then fetch it.
- Follow company policies from the wiki.
- Do not ask the user to choose; use available tools and infer the best option.
- When updating an entry, include all fields (carry forward unchanged values).
- When the task is complete or cannot be completed, call `Req_ProvideAgentResponse` exactly once with one of these outcomes:
    - `ok_answer` - task completed (no access or other violations of the company policy)
    - `ok_not_found` - the requested entity/resource was searched for but not found
    - `denied_security` - access denied or policy violation. the action cannot be performed due to access control or policy restrictions.
    - `none_clarification_needed` - more input is required from the system to proceed but it cannot be obtained through the available tools.
    - `none_unsupported` - the request is outside the agent's capabilities or the system policy (e.g., unsupported operation)
    - `error_internal` - an internal error occurred while trying to perform the task.

# Current user info:
{about.model_dump_json()}
"""
    if about.current_user:
        usr = store_api.get_employee(about.current_user)
        instructions += f"\n{usr.model_dump_json()}"

    started = time.time()

    # Create the CodeAgent with store tools
    hf_coding_agent = CodeAgent(
        tools=tools,
        model=usage_tracking_model,
        additional_authorized_imports=["datetime", "json"],
        prompt_templates=prompt_templates,
        instructions=instructions,
    )

    # Prepare the task with system context
    task_prompt = f"""Task to complete: {task.task_text}"""

    try:
        logging.info(
            f"{CLI_GREEN}[AGENT]{CLI_CLR} Starting agent execution with model: {usage_tracking_model.model_id}"
        )

        logging.info(f"System Prompt:\n{hf_coding_agent.system_prompt}")

        logging.info("=" * 80)

        # Run the agent
        result = hf_coding_agent.run(task_prompt)

        duration = time.time() - started
        logging.info(
            f"{CLI_GREEN}[SUCCESS]{CLI_CLR} Agent completed task in {duration:.2f}s"
        )
        logging.info(f"{CLI_GREEN}[RESULT]{CLI_CLR} {result}")
        logging.info(f"Total token usage: {usage_tracking_model.total_usage}")

        # Note: SmolAgents doesn't provide direct access to usage stats like OpenAI
        # For now, we'll log with minimal information
        api.log_llm(
            task_id=task.task_id,
            model=usage_tracking_model.model_name_for_logging,
            duration_sec=duration,
            usage=usage_tracking_model.total_usage,
        )

    except Exception as e:
        duration = time.time() - started
        logging.info(
            f"{CLI_RED}[FAILED]{CLI_CLR} Agent failed after {duration:.2f}s: {str(e)}"
        )
    finally:
        logging.info(
            f"{CLI_GREEN}[CLEANUP]{CLI_CLR} Agent session ended, task {task.task_id}"
        )
