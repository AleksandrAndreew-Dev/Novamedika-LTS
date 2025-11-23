import aiohttp
from aiohttp_retry import RetryClient, ExponentialRetry
import xml.etree.ElementTree as ET
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BaseAPIProvider(ABC):
    """Абстрактный базовый класс для провайдеров API"""

    def __init__(self, endpoint: str, auth_token: str, auth_type: str = "bearer"):
        self.endpoint = endpoint
        self.auth_token = auth_token
        self.auth_type = auth_type

    @abstractmethod
    async def submit_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_orders(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def update_order_status(self, external_order_id: str, status: str) -> bool:
        pass

class JSONAPIProvider(BaseAPIProvider):
    """Провайдер для JSON API"""

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.auth_type == "bearer":
            headers["Authorization"] = f"Bearer {self.auth_token}"
        elif self.auth_type == "api_key":
            headers["X-API-Key"] = self.auth_token
        return headers

    async def submit_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.endpoint}/orders",
                json=order_data,
                headers=self._get_headers()
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"API error: {response.status}")

    async def get_orders(self, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        params = {}
        if since:
            params["since"] = since.isoformat()

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.endpoint}/orders",
                params=params,
                headers=self._get_headers()
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("orders", [])
                else:
                    raise Exception(f"API error: {response.status}")

    async def update_order_status(self, external_order_id: str, status: str) -> bool:
        async with aiohttp.ClientSession() as session:
            async with session.patch(
                f"{self.endpoint}/orders/{external_order_id}",
                json={"status": status},
                headers=self._get_headers()
            ) as response:
                return response.status == 200


# В manager.py - нужно реализовать
class ExternalAPIManager:
    async def submit_order_to_pharmacy(self, api_config, payload):
        # TODO: реализовать отправку заказа в аптеку
        # В зависимости от api_config.api_type используйте соответствующий провайдер
        if api_config.api_type == "json":
            provider = JSONAPIProvider(
                api_config.endpoint_url,
                api_config.get_auth_token(),
                api_config.auth_type
            )
            return await provider.submit_order(payload)
        # Добавьте обработку других типов API
        pass

    async def sync_orders_from_pharmacy(self, api_config, since):
        # TODO: реализовать получение заказов из аптеки
        return []
