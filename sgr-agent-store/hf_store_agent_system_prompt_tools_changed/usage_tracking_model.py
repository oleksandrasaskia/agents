from smolagents import LiteLLMModel
from smolagents.models import ChatMessage
from pydantic import BaseModel
import logging


class TokenUsage(BaseModel):
    """Pydantic model for token usage tracking (OpenAI-compatible format)"""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class UsageTrackingModel(LiteLLMModel):
    """
    A wrapper around LiteLLMModel that:
      - tracks usage of every LLM call
      - automatically aggregates token usage
      - keeps the original LiteLLMModel behavior intact
    """

    def __init__(self, *args, model_name_for_logging: str = None, **kwargs):
        super().__init__(*args, **kwargs)

        self.total_usage = TokenUsage()
        self.last_usage = None  # usage of the most recent call

        # must match slug from OpenRouter:
        self.model_name_for_logging = model_name_for_logging or (
            self.model_id if isinstance(self.model_id, str) else "unknown_model"
        )

    def generate(self, messages, *args, **kwargs) -> ChatMessage:
        logging.info("Calling UsageTrackingModel.generate()...")
        # Perform the normal LiteLLMModel generate call
        response: ChatMessage = super().generate(messages, *args, **kwargs)

        # Extract token_usage from the ChatMessage (smolagents format)
        if response.token_usage:
            prompt_tokens = response.token_usage.input_tokens
            completion_tokens = response.token_usage.output_tokens
            usage = TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            )
            logging.info(f"LLM Call Usage: {usage}")

            # Store last usage
            self.last_usage = usage

            # Update aggregated totals
            self.total_usage.prompt_tokens += usage.prompt_tokens
            self.total_usage.completion_tokens += usage.completion_tokens
            self.total_usage.total_tokens += usage.total_tokens
        else:
            logging.warning("No token_usage in response")

        return response
