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

from hf_store_agent_tools import (
    ListProductsTool,
    ViewBasketTool,
    ApplyCouponTool,
    RemoveCouponTool,
    AddProductToBasketTool,
    RemoveItemFromBasketTool,
    CheckoutBasketTool,
    FinalAnswerTool,
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


instructions = """

Goal: Complete the given task by interacting with the store using the available tools, tools call API of the online store.

Rules to follow for the store interaction:
1. Start by listing **all at the moment available** products with `list_products`. Stop pagination when `next_offset` == -1 (use `limit` up to 3). Never invent SKUs, product names, prices, quantities, or coupon codes — use values exactly as returned by the tools.
2. Build an internal catalog: name, SKU, available quantity, price, and other features. Utilize the fields of the products to compare prices, etc. Match the task to catalog items by comparing names and features of products.
3. Before adding, confirm the item's `available` value; never add more than `available`.
4. When adding, call `add_product_to_basket(sku, quantity)`, then call `view_basket()` to confirm.
5. Coupons: 
    - only one coupon can be applied at the same time
    - use `apply_coupon(coupon)` then `view_basket()` to verify discount and totals
    - use `remove_coupon()` if you need to remove coupon
    - compute which coupon yields the **largest discount**
    - coupons can be mutually exclusive
    - coupon codes can be invalid
    - analyse all given coupons to get the best discount
6. Tools may return API errors (e.g., insufficient stock at checkout). Respond to tool outputs and adjust actions accordingly.
7. When you call checkout_basket(), there can be insufficient stock errors. Make sure to get the response from checkout_basket() before proceeding. Do not buy partial amounts if stock is insufficient.
8. If it is not possible to do what the task requires, **do not** checkout partial amounts.
9. You can do only one checkout_basket() call per task.
10. Call checkout_basket() to complete the purchase and task when possible. End the session by calling `final_answer(answer)` with a concise summary: purchased items (name, SKU, quantity, unit price, subtotal), applied coupon and discount, final total, and any adjustments made. **Important**: Before calling final_answer(), review the rules and check that there is nothing you missed. If mistakes were made, correct them before finalizing.    adjustments made. **Important**: Before calling final_answer(), review the rules and check that there is nothing you missed. If mistakes were made, correct them before finalizing.

Tasks can be not achievable on purpose, and provide invalid input as they come from users. Carefully consider product features, prices, stock levels, and coupon interactions. Always rely on the exact data returned by the tools and follow the rules strictly.
"""

instructions_gpt5_mini_optimized = """
Store Task Execution Protocol

Objective: Complete the user task by interacting with the store ONLY via the provided tools. Finish with ONE checkout (if feasible) then ONE final_answer summary.

Workflow Overview:
1. Enumerate products first: call list_products with pagination (limit <= 3); stop when next_offset == -1. NEVER invent product / SKU / price / quantity / coupon data.
2. Build an internal catalog: for each product capture {name, sku, available, price, attributes}. Use only returned fields. Use this for matching and comparisons.
3. Validate stock before adding; never request quantity > available.
4. Add flow: add_product_to_basket(sku, qty) THEN view_basket() to verify state.
5. Coupons strategy:
    - Collect candidate coupon codes from task or tool outputs.
    - Test each: apply_coupon(code) -> view_basket(); record discount delta.
    - Keep BEST single coupon only; remove_coupon() before trying the next.
    - Handle invalid / mutually exclusive coupons gracefully.
6. Error handling: On any API error (insufficient stock, invalid coupon, etc.) adapt plan using ONLY tool outputs; do not proceed blindly.
7. Checkout logic: Attempt checkout ONLY when basket fully satisfies task. Call checkout_basket() ONCE. If insufficient stock error appears, DO NOT partial checkout; abort purchase.
8. If task cannot be satisfied (missing product, insufficient stock, etc.) do NOT checkout.
9. Completion protocol:
    - Before final_answer(): re-check rules; if mistakes found, fix first.
    - final_answer(summary) MUST include:
      * Items: name, sku, quantity, unit_price, per-item subtotal
      * Applied coupon (or 'none') and discount amount
      * Final total
      * Adjustments / decisions (coupon choice rationale, stock constraints)
    - NEVER fabricate numbers—echo only tool-derived values.

Key DOs:
- DO rely strictly on tool outputs.
- DO keep internal catalog consistent after each listing page.
- DO recompute best coupon only from observed basket totals.

Key DON'Ts:
- DON'T invent SKUs, prices, quantities, coupon codes.
- DON'T add more than available stock.
- DON'T call checkout_basket() more than once.
- DON'T perform partial fulfillment.

Remember: Tasks may be impossible; detect and report clearly instead of forcing checkout.
"""


instructions_gpt5_mini_optimized_cost_effective = """
Store Task Execution Protocol — Cost-Effective Purchase

Objective: Fulfill the user’s request at the lowest total cost using ONLY the provided tools. Prefer a single checkout when feasible; end with ONE final_answer summary.

Primary Scenario (example): "Buy 1x Office Laser Printer as cheaply as possible. You may optionally add paper or accessories. Coupons to try: PRINT10, BUNDLE30."

Workflow:
1) Discover products first:
    - Call list_products with pagination (limit <= 3); stop when next_offset == -1.
    - NEVER invent product/SKU/price/quantity/coupon data.
    - Build an internal catalog: {name, sku, available, price, attributes} strictly from tool outputs.

2) Identify target product(s):
    - Match by name/features (e.g., "Office Laser Printer").
    - If multiple candidates exist, choose the cheapest printer that meets the task.
    - Confirm stock: desired qty <= available.

3) Basket construction strategy (cost-first):
    - Add the chosen printer: add_product_to_basket(sku, 1) → view_basket() to verify.
    - Optional items (paper/accessories): only add if they reduce final total (e.g., unlock better bundle savings) or are requested explicitly.
    - If exploring optional items for bundles, add ONE candidate at a time and measure impact; keep the cheapest configuration.

4) Coupon evaluation protocol:
    - Candidate coupons come from the task or tool outputs (e.g., PRINT10, BUNDLE30).
    - For each coupon: apply_coupon(code) → view_basket(); record discount and final total.
    - If coupons are mutually exclusive, remove_coupon() before trying the next.
    - Choose the single coupon that yields the lowest final total for the basket configuration.
    - If adding optional items enables a better coupon (e.g., bundle), compare totals WITH and WITHOUT those items; keep the cheaper overall outcome.

5) Error handling:
    - On any API error (invalid coupon, insufficient stock, etc.), adapt using ONLY tool outputs.
    - Do not proceed blindly; re-check basket and catalog.

6) Checkout rules:
    - Attempt checkout ONLY when basket satisfies the task and is the cheapest confirmed configuration.
    - Call checkout_basket() ONCE.
    - If insufficient stock at checkout, DO NOT partial-fulfill; abort purchase.

7) Completion:
    - Before final_answer(), re-check rules and basket consistency.
    - final_answer(summary) MUST include:
      * Items: name, sku, quantity, unit_price, per-item subtotal
      * Applied coupon (or 'none') and discount amount
      * Final total
      * Rationale: why this configuration is cheapest (e.g., coupon comparison, bundle impact)
    - NEVER fabricate numbers—use only tool-returned values.

Key DOs:
- DO prioritize lowest final payable total (including discounts).
- DO compare printer-only vs. printer+optional configurations if coupons suggest savings.
- DO keep internal catalog up-to-date per listing page.

Key DON'Ts:
- DON'T invent SKUs, prices, quantities, or coupon codes.
- DON'T add more than available stock.
- DON'T call checkout_basket() more than once.
- DON'T perform partial fulfillment.

If the task is impossible (product missing or insufficient stock), clearly report via final_answer without checkout.
"""


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
    log_filename = (
        f"logs/{workspace_name}/agent_run_{workspace_name}_{task.task_id}.log"
    )
    # Ensure the log directory exists before configuring logging
    log_dir = os.path.dirname(log_filename)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_filename, mode="w", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    # Enable DEBUG logging for smolagents to see full reasoning/thinking
    logging.getLogger("smolagents").setLevel(logging.DEBUG)

    logging.info(f"{CLI_GREEN}[INIT]{CLI_CLR} Starting agent for task: {task.task_id}")
    logging.info(f"{CLI_GREEN}[TASK]{CLI_CLR} {task.task_text}")
    logging.info(f"Agent started for task {task.task_id}: {task.task_text}")

    store_api = api.get_store_client(task)

    # Create all the tools for the agent
    logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} About to create tools...")
    tools = []

    try:
        logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating ListProductsTool...")
        tools.append(ListProductsTool(store_api))
        logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating ViewBasketTool...")
        tools.append(ViewBasketTool(store_api))
        logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating ApplyCouponTool...")
        tools.append(ApplyCouponTool(store_api))
        logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating RemoveCouponTool...")
        tools.append(RemoveCouponTool(store_api))
        logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating AddProductToBasketTool...")
        tools.append(AddProductToBasketTool(store_api))
        logging.info(
            f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating RemoveItemFromBasketTool..."
        )
        tools.append(RemoveItemFromBasketTool(store_api))
        logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating CheckoutBasketTool...")
        tools.append(CheckoutBasketTool(store_api))
        logging.info(f"{CLI_GREEN}[DEBUG]{CLI_CLR} Creating FinalAnswerTool...")
        tools.append(FinalAnswerTool())
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

    started = time.time()

    # Create the CodeAgent with store tools
    hf_coding_agent = CodeAgent(
        tools=tools,
        model=usage_tracking_model,
        additional_authorized_imports=["datetime", "json"],
        prompt_templates=prompt_templates,
        instructions=instructions_gpt5_mini_optimized_cost_effective,
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
