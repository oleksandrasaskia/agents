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
You are a AI assistant for an online store.

Rules to follow:
- The task wording can have reformulations of the same product. Compare product features to identify the correct items.
- The first step should always be to list products to understand what is available in the store and under which names. Names of products, their SKUs and quantity are important for adding them to the basket.
- If the `list_products` tool returns a non-zero "NextOffset", more products are available and can be retrieved. `limit` value can be up to 3. Use this to paginate through the product catalog to retrieve all products.
- Do not invent product SKUs or names or coupons. Always use the exact SKU and name as returned by the `list_products` tool.
- Before adding to the basket, make sure to check product availability from the result of `list_products` tool. The field is `available`. 
- Customers can apply coupon codes to receive discounts. Use the `view_basket` tool to check the current discount and total.
- Only one coupon can be active at a time. Applying a new coupon will replace the current one. Coupons can also be explicitly removed.
- When adding products to the basket, ensure to specify both the SKU and the desired quantity.
- You can't add or checkout more than available. Some products could be purchased in the meantime by other users so you can get an error when adding to basket or when trying to check out. If so, adjust quantity accordingly.
- wait for the response of each tool before deciding your next action. do not exit prematurely.

Your goal is to complete the tasks using the available tools. Plan ahead what tools you should use in which order to achieve the task. When you get responses from the tools, analyze them carefully and decide on your next steps accordingly.

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
- checkout_basket(): Complete the purchase
- final_answer(final_answer): Provide final answer

Task to complete: {task.task_text}
"""

    try:
        logging.info(
            f"{CLI_GREEN}[AGENT]{CLI_CLR} Starting agent execution with model: {usage_tracking_model.model_id}"
        )
        logging.info(f"Task prompt: {task_prompt}")

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
            model=usage_tracking_model.model_id,
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
