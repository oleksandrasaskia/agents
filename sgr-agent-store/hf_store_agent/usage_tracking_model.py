from smolagents import LiteLLMModel
from smolagents.models import ChatMessage
import logging


class UsageTrackingModel(LiteLLMModel):
    """
    A wrapper around LiteLLMModel that:
      - tracks usage of every LLM call
      - automatically aggregates token usage
      - keeps the original LiteLLMModel behavior intact
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.total_usage = {
            "input_tokens": 0,
            "output_tokens": 0,
        }
        self.last_usage = None  # usage of the most recent call

    def generate(self, messages, *args, **kwargs) -> ChatMessage:
        logging.info("Calling UsageTrackingModel.generate()...")
        # Perform the normal LiteLLMModel generate call
        response: ChatMessage = super().generate(messages, *args, **kwargs)

        # Extract token_usage from the ChatMessage (smolagents format)
        if response.token_usage:
            usage = {
                "input_tokens": response.token_usage.input_tokens,
                "output_tokens": response.token_usage.output_tokens,
            }
            logging.info(f"LLM Call Usage: {usage}")

            # Store last usage
            self.last_usage = usage

            # Update aggregated totals
            self.total_usage["input_tokens"] += usage.get("input_tokens", 0)
            self.total_usage["output_tokens"] += usage.get("output_tokens", 0)
        else:
            logging.warning("No token_usage in response")

        return response
