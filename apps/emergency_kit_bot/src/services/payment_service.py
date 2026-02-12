from abc import ABC, abstractmethod
from src.db.models import Order

class PaymentProvider(ABC):
    @abstractmethod
    async def create_payment(self, order: Order) -> str:
        pass

    @abstractmethod
    async def verify_payment(self, payment_data: dict) -> bool:
        pass

class MockGatewayProvider(PaymentProvider):
    async def create_payment(self, order: Order) -> str:
        # Simulate generating a gateway URL
        return f"https://mock-gateway.com/pay/{order.order_code}"

    async def verify_payment(self, payment_data: dict) -> bool:
        # Simulate verification logic
        return True

# To be implemented for actual Iranian gateways
class ZarinPalProvider(PaymentProvider):
    async def create_payment(self, order: Order) -> str:
        # Stub for ZarinPal integration
        return "https://zarinpal.com/pay/stub"

    async def verify_payment(self, payment_data: dict) -> bool:
        return False
