import os
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
You are a business assistant helping customers of OnlineStore.

- Clearly report when tasks are done.
- If ListProducts returns non-zero "NextOffset", it means there are more products available.
- You can apply coupon codes to get discounts. Use ViewBasket to see current discount and total.
- Only one coupon can be applied at a time. Apply a new coupon to replace the current one, or remove it explicitly.
"""


CLI_RED = "\x1b[31m"
CLI_GREEN = "\x1b[32m"
CLI_CLR = "\x1b[0m"


def run_agent(model: str, api: ERC3, task: TaskInfo):
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

    usage_tracking_model = UsageTrackingModel(  # LiteLLMModel(
        model_id=model, api_key=os.getenv("GEMINI_API_KEY")
    )

    # Create the CodeAgent with store tools
    hf_coding_agent = CodeAgent(
        tools=tools,
        model=usage_tracking_model,
        additional_authorized_imports=["datetime", "json"],
    )

    # Prepare the task with system context
    task_prompt = f"""
{system_prompt}

Task to complete: {task.task_text}

Available tools:
- list_products(offset, limit): List products in the store
- view_basket(): View current basket contents and totals
- apply_coupon(coupon): Apply a discount coupon
- remove_coupon(): Remove current coupon
- add_product_to_basket(sku, quantity): Add product to basket
- remove_item_from_basket(sku, quantity): Remove item from basket
- checkout_basket(): Complete the purchase
- final_answer(final_answer): Provide final answer for the task once completed or if it is not possible to complete after all the retries
"""

    try:
        logging.info(
            f"{CLI_GREEN}[AGENT]{CLI_CLR} Starting agent execution with model: {model}"
        )
        logging.info(f"Agent execution started with model: {model}")
        logging.info(f"Task prompt: {task_prompt}")

        # Run the agent
        result = hf_coding_agent.run(task_prompt)

        duration = time.time() - started
        logging.info(
            f"{CLI_GREEN}[SUCCESS]{CLI_CLR} Agent completed task in {duration:.2f}s"
        )
        logging.info(f"{CLI_GREEN}[RESULT]{CLI_CLR} {result}")
        logging.info(f"Agent completed successfully in {duration:.2f}s")
        logging.info(f"Final result: {result}")
        logging.info(f"Total token usage: {usage_tracking_model.total_usage}")

        # Note: SmolAgents doesn't provide direct access to usage stats like OpenAI
        # For now, we'll log with minimal information
        api.log_llm(
            task_id=task.task_id,
            model=model,
            duration_sec=duration,
            usage=usage_tracking_model.total_usage,
        )
        logging.info(f"Logged LLM usage to ERC3 API")

    except Exception as e:
        duration = time.time() - started
        logging.info(
            f"{CLI_RED}[FAILED]{CLI_CLR} Agent failed after {duration:.2f}s: {str(e)}"
        )
        logging.error(f"Agent failed after {duration:.2f}s: {str(e)}")

        api.log_llm(
            task_id=task.task_id,
            model=model,
            duration_sec=duration,
            usage=usage_tracking_model.total_usage,
        )
        logging.info(f"Logged failed LLM usage to ERC3 API")

    finally:
        logging.info(f"{CLI_GREEN}[CLEANUP]{CLI_CLR} Agent session ended")
        logging.info(f"Agent session completed for task {task.task_id}")
