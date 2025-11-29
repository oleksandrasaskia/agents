import logging
from erc3 import store, ApiException
from smolagents import Tool

CLI_RED = "\x1b[31m"
CLI_GREEN = "\x1b[32m"
CLI_CLR = "\x1b[0m"


class StoreAPITool(Tool):
    """Base class for store API tools"""

    def __init__(self):
        # Initialize Tool with proper attributes - subclasses will set specific values
        super().__init__()

    def _execute_api_call(self, **kwargs) -> str:
        # Log tool invocation
        logging.info(f"{CLI_GREEN}[TOOL]{CLI_CLR} {self.name} called with: {kwargs}")

        try:
            # Create request object from kwargs
            request = self.request_class(**kwargs)
            logging.info(f"{CLI_GREEN}[REQUEST]{CLI_CLR} {type(request)} -> {request}")

            if request is not None:
                if isinstance(request, dict):
                    logging.info(
                        f"{CLI_GREEN}[API]{CLI_CLR} Executing {self.request_class.__name__}: {request}"
                    )
                else:
                    logging.info(
                        f"{CLI_GREEN}[API]{CLI_CLR} Executing {self.request_class.__name__}: {request.model_dump()}"
                    )

            # Execute the API call
            result = self.store_api.dispatch(request)

            # Handle case where API returns None
            if result is not None:
                # Handle both Pydantic models and plain dicts
                if isinstance(result, dict):
                    import json

                    result_json = json.dumps(result)
                else:
                    result_json = result.model_dump_json(
                        exclude_none=True, exclude_unset=True
                    )

                logging.info(
                    f"{CLI_GREEN}[RESULT]{CLI_CLR} {self.name} -> {result_json}"
                )

                return result_json
            else:
                logging.info(f"{CLI_GREEN}[RESULT]{CLI_CLR} {self.name} -> No content")
                return "No content"
        except ApiException as e:
            error_msg = f"API Error: {e.api_error.error}"
            logging.info(f"{CLI_RED}[ERROR]{CLI_CLR} {self.name} -> {error_msg}")
            return error_msg
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            logging.info(f"{CLI_RED}[ERROR]{CLI_CLR} {self.name} -> {error_msg}")
            return error_msg


class ListProductsTool(StoreAPITool):
    def __init__(self, store_api):
        self.name = "list_products"
        self.description = "List available products in the store. Required parameters: offset (int), limit (int)"
        self.inputs = {
            "offset": {
                "type": "integer",
                "description": "Starting offset for pagination",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of products to return",
            },
        }
        self.output_type = "string"
        self.store_api = store_api
        self.request_class = store.Req_ListProducts
        super().__init__()
        logging.info(f"DEBUG: Initialized tool: {self.name}")

    def forward(self, offset: int, limit: int) -> str:
        return self._execute_api_call(offset=offset, limit=limit)


class ViewBasketTool(StoreAPITool):
    def __init__(self, store_api):
        self.name = "view_basket"
        self.description = (
            "View current shopping basket contents, totals, and applied coupons"
        )
        self.inputs = {}  # No parameters required
        self.output_type = "string"
        self.store_api = store_api
        self.request_class = store.Req_ViewBasket
        super().__init__()
        logging.info(f"DEBUG: Initialized tool: {self.name}")

    def forward(self) -> str:
        return self._execute_api_call()


class ApplyCouponTool(StoreAPITool):
    def __init__(self, store_api):
        self.name = "apply_coupon"
        self.description = (
            "Apply a coupon code to get discount. Required parameter: coupon (str)"
        )
        self.inputs = {
            "coupon": {"type": "string", "description": "Coupon code to apply"}
        }
        self.output_type = "string"
        self.store_api = store_api
        self.request_class = store.Req_ApplyCoupon
        super().__init__()
        logging.info(f"DEBUG: Initialized tool: {self.name}")

    def forward(self, coupon: str) -> str:
        return self._execute_api_call(coupon=coupon)


class RemoveCouponTool(StoreAPITool):
    def __init__(self, store_api):
        self.name = "remove_coupon"
        self.description = "Remove currently applied coupon"
        self.inputs = {}  # No parameters required
        self.output_type = "string"
        self.store_api = store_api
        self.request_class = store.Req_RemoveCoupon
        super().__init__()
        logging.info(f"DEBUG: Initialized tool: {self.name}")

    def forward(self) -> str:
        return self._execute_api_call()


class AddProductToBasketTool(StoreAPITool):
    def __init__(self, store_api):
        self.name = "add_product_to_basket"
        self.description = "Add a product to the shopping basket. Required parameters: sku (str), quantity (int, default=1)"
        self.inputs = {
            "sku": {"type": "string", "description": "Product SKU to add"},
            "quantity": {"type": "integer", "description": "Quantity to add"},
        }
        self.output_type = "string"
        self.store_api = store_api
        self.request_class = store.Req_AddProductToBasket
        super().__init__()
        logging.info(f"DEBUG: Initialized tool: {self.name}")

    def forward(self, sku: str, quantity: int) -> str:
        return self._execute_api_call(sku=sku, quantity=quantity)


class RemoveItemFromBasketTool(StoreAPITool):
    def __init__(self, store_api):
        self.name = "remove_item_from_basket"
        self.description = "Remove an item from the shopping basket. Required parameters: sku (str), quantity (int)"
        self.inputs = {
            "sku": {"type": "string", "description": "Product SKU to remove"},
            "quantity": {"type": "integer", "description": "Quantity to remove"},
        }
        self.output_type = "string"
        self.store_api = store_api
        self.request_class = store.Req_RemoveItemFromBasket
        super().__init__()
        logging.info(f"DEBUG: Initialized tool: {self.name}")

    def forward(self, sku: str, quantity: int) -> str:
        return self._execute_api_call(sku=sku, quantity=quantity)


class CheckoutBasketTool(StoreAPITool):
    def __init__(self, store_api):
        self.name = "checkout_basket"
        self.description = "Complete the checkout process for items in the basket"  # 	Checkout and complete purchase
        self.inputs = {}  # No parameters required
        self.output_type = "string"
        self.store_api = store_api
        self.request_class = store.Req_CheckoutBasket
        super().__init__()
        logging.info(f"DEBUG: Initialized tool: {self.name}")

    def forward(self) -> str:
        return self._execute_api_call()


class FinalAnswerTool(Tool):
    """Tool for providing final task completion summary"""

    def __init__(self):
        self.name = "final_answer"
        self.description = "Provide a final summary when the task is completed or if it is not possible to complete it after reviewing all rules and ensuring full compliance. Required parameter: answer (str)"
        self.inputs = {
            "answer": {
                "type": "string",
                "description": "The final answer to return.",
            }
        }
        self.output_type = "string"
        super().__init__()
        logging.info(f"DEBUG: Initialized tool: {self.name}")

    def forward(self, answer: str) -> str:
        logging.info(f"{CLI_GREEN}[FINAL]{CLI_CLR} Task completed: {answer}")

        return answer
