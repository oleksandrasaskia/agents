import time
import logging
from erc3 import TaskInfo, ERC3
from smolagents import CodeAgent

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


system_prompt = """
You are an AI assistant for an online store. Use only the provided tools and act only on the exact structured data those tools return.

Goal: Complete the given task by interacting with the store using the available tools, tools call API of the online store.

Rules to follow:
1. Start by listing **all at the moment available** products with `list_products`. Page until `next_offset` is -1 (use `limit` up to 3). Never invent SKUs, product names, prices, quantities, or coupon codes — use values exactly as returned by the tools.
2. Build an internal catalog: name, SKU, available quantity, price, and other features. Utilize the fields of the products to compare prices, etc. Match the task to catalog items by comparing names and features of products.
3. Before adding, confirm the item's `available` value; never add more than `available`.
4. When adding, call `add_product_to_basket(sku, quantity)`, then call `view_basket()` to confirm.
5. Coupons: 
    - only one coupon can be applied at the same time!
    - use `apply_coupon(coupon)` then `view_basket()` to verify discount and totals
    - use `remove_coupon()` if you need to remove coupon
    - compute which coupon yields the largest discount
    - coupons can be mutually exclusive
    - coupon codes can be invalid
    - analyse all given coupons to get the best discount
6. Tools may return API errors (e.g., insufficient stock at checkout). Respond to tool outputs and adjust actions accordingly.
7. When you call checkout_basket(), there can be insufficient stock errors. Make sure to get the response from checkout_basket() before proceeding. Do not buy partial amounts if stock is insufficient.
8. If it is not possible to do what the task requires, **do not** checkout partial amounts.
9. Call checkout_basket() to complete the purchase and task when possible. End the session by calling `final_answer(answer)` with a concise summary: purchased items (name, SKU, quantity, unit price, subtotal), applied coupon and discount, final total, and any adjustments made. **Important**: Before calling final_answer(), review the rules and check that there is nothing you missed. If mistakes were made, correct them before finalizing.    adjustments made. **Important**: Before calling final_answer(), review the rules and check that there is nothing you missed. If mistakes were made, correct them before finalizing.

Tasks can be not achievable on purpose, and provide invalid input as they come from users. Carefully consider product features, prices, stock levels, and coupon interactions. Always rely on the exact data returned by the tools and follow the rules strictly.
"""


CLI_RED = "\x1b[31m"
CLI_GREEN = "\x1b[32m"
CLI_CLR = "\x1b[0m"


def run_agent(usage_tracking_model: UsageTrackingModel, api: ERC3, task: TaskInfo):
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
        ],
    )

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
    )

    # Prepare the task with system context
    task_prompt = f"""
{system_prompt}

Available tools:
- list_products(offset, limit): List products in the store
- view_basket(): View current basket contents and totals
- apply_coupon(coupon): Apply a discount coupon
- remove_coupon(): Remove current coupon
- add_product_to_basket(sku, quantity): Add product to basket
- remove_item_from_basket(sku, quantity): Remove item from basket
- checkout_basket(): Checkout items in the basket and complete the purchase
- final_answer(final_answer): Provide final answer

Task to complete: {task.task_text}
"""

    try:
        logging.info(
            f"{CLI_GREEN}[AGENT]{CLI_CLR} Starting agent execution with model: {usage_tracking_model.model_id}"
        )

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
