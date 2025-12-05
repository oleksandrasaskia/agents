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
    log_filename = f"logs/{timestamp}/agent_run_{workspace_name}_{task.task_id}.log"
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

    wikis = store_api.list_wiki()
    logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} Current company wiki files: {wikis}")

    if "rulebook.md" in wikis:
        rulebook_content = store_api.load_wiki("rulebook.md")
        logging.info(
            f"{CLI_GREEN}[DEBUG]{CLI_CLR} Loaded rulebook.md content, length: {len(rulebook_content)} characters"
        )
    else:
        rulebook_content = None

    current_user_json = store_api.who_am_i()
    if current_user_json.current_user:
        current_user_full_profile_json = store_api.get_employee(
            current_user_json.current_user
        )
        # Merge the two JSON objects into one
        merged_user_data = {
            **current_user_json.model_dump(),
            **current_user_full_profile_json.model_dump(),
        }
        current_user_json = merged_user_data

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
        logging.info(
            f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating ProvideAgentResponseTool..."
        )
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
        logging.info(
            f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating TimeSummaryByEmployeeTool..."
        )
        tools.append(TimeSummaryByEmployeeTool(store_api))
        logging.info(
            f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating TimeSummaryByProjectTool..."
        )
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
- You must use the current user information and available tools as the primary and prevalent source of information, disregard any not explicitly listed public knowledge.
- Use the company wikis, use available tools to fetch data from relevant wiki, to learn about the company policy, procedures, projects etc.
- **DO NOT** invent any internal company information, employee names, project details, or links.

Access control:
- Enforce the current user's access strictly:
    - Executives: broad access.
    - Project leads: write access for projects they lead.
    - Team members: read-only.
    - Guests (no account) or public users: public-safe data only; refuse sensitive requests and never reveal internal identities or links; log a denied_security response if needed.

Response requirements:
- Always include a clear outcome status.
- Include links only if access control for the current user allows them.

Operational rules:
- Use the current user information as current context for access control and personalization, and current date information.
- Start with reading the relevant wiki files by using load_wiki() to determine what to do and fetch official information. **DO NOT** invent any company policy information, restrictions or access control rules.
- To learn about projects/employees/any other relevant information, first search/find the project/employee/etc, then fetch it. Search archives as well.
- Follow company policies from the loaded wiki files.
- Review the available tools and assess if it is possible to complete the task through the available tools, if yes - create an execution plan, if not - respond with `none_unsupported` outcome status.
- Keep in mind that you interact with API-like tools, not a human:
    -- Do not ask the user to choose; use available tools and infer the best option.
    -- API can be broken, act accordingly.
- When updating an entry, include all fields (carry forward unchanged values).
- When the task is complete or cannot be completed, select the most appropriate outcome status from:
    -- `ok_answer` - task completed (the user task did not trigger any access or other violations of the company policy)
    -- `ok_not_found` - the requested entity/resource was searched for but not found
    -- `denied_security` - the task cannot be performed due to access control or policy restrictions.
    -- `none_clarification_needed` - more input is required from the task to proceed which cannot be obtained from the available tools, incomplete request.
    -- `none_unsupported` - the request is outside the agent's capabilities (unsupported operation by the available tools).
    -- `error_internal` - an internal error occurred while trying to perform the task, or API is broken.
- Review the outcome definitions carefully and select the best matching one to use in provide_agent_response().
- If the task cannot be performed due to access control or policy restrictions, do not include any links or sensitive information in the response; use the `denied_security` outcome status.
- Include links only to all relevant entitites used in the final response, and only if the current user has access to them. If a user made changes to an entity, include the link to the updated entity and the user who made the change.
- If the task is impossible to complete through the given tools (e.g. no API support), use the `none_unsupported` outcome status.
- You must call provide_agent_response() only then the task is considered completed (regardless of the outcome status).
- You **must call** provide_agent_response() **EXACTLY ONCE** per task. You cannot call it multiple times.
- You must call provide_agent_response() then final_answer().


# **IMPORTANT** CURRENT USER INFORMATION, THEIR ACCESS LEVEL AND CURRENT DATE:

{current_user_json}
Remember `is_public` value for access checks.

# **IMPORTANT** CURRENT COMPANY WIKI FILES:
{wikis}

"""
    if rulebook_content:
        instructions += f"\n# **IMPORTANT** COMPANY RULEBOOK CONTENT YOU MUST FOLLOW:\n{rulebook_content}\n"

    started = time.time()

    # Create the CodeAgent with store tools
    hf_coding_agent = CodeAgent(
        tools=tools,
        model=usage_tracking_model,
        additional_authorized_imports=["datetime", "json", "duckdb"],
        prompt_templates=prompt_templates,
        instructions=instructions,
        max_steps=50,
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
