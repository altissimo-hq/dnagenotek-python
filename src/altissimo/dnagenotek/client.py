"""DNA Genotek API client."""

from __future__ import annotations

import base64
import logging
import os
from dataclasses import dataclass
from typing import Any

import requests

from altissimo.dnagenotek.exceptions import DNAGenotekAuthenticationError
from altissimo.dnagenotek.models import (
    CreateDNAGenotekAPIOrderRequest,
    DNAGenotekAPIListOrdersParams,
    DNAGenotekAPIOrder,
    DNAGenotekDestination,
    DNAGenotekKit,
    DNAGenotekLabel,
    DNAGenotekOrderItem,
)

logger = logging.getLogger(__name__)


def _api_order_from_dict(data: dict[str, Any]) -> DNAGenotekAPIOrder:
    """Build a DNAGenotekAPIOrder from a raw API response dict."""
    destination_data = data.pop("destination")
    destination = DNAGenotekDestination(**destination_data)

    items_data = data.pop("items")
    items = [DNAGenotekOrderItem(**item) for item in items_data]

    kits_data = data.pop("kits")
    kits = [DNAGenotekKit(**kit) for kit in kits_data] if kits_data is not None else None

    labels_data = data.pop("labels")
    labels = [DNAGenotekLabel(**label) for label in labels_data] if labels_data is not None else None

    return DNAGenotekAPIOrder(
        destination=destination,
        items=items,
        kits=kits,
        labels=labels,
        **data,
    )


@dataclass(frozen=True)
class DNAGenotekSettings:
    """Settings for DNAGenotek API client."""

    api_key: str
    base_url: str
    timeout: int = 10

    @classmethod
    def from_env(
        cls,
        *,
        api_key_env: str = "DNAGENOTEK_API_KEY",
        base_url_env: str = "DNAGENOTEK_BASE_URL",
    ) -> DNAGenotekSettings:
        """Build settings from environment variables."""
        api_key = os.environ.get(api_key_env, "")
        base_url = os.environ.get(base_url_env, "")
        if not api_key:
            raise ValueError(f"{api_key_env} is not set")
        if not base_url:
            raise ValueError(f"{base_url_env} is not set")
        return cls(api_key=api_key, base_url=base_url)


class DNAGenotekClient:
    """Thin client for DNAGenotek external API."""

    def __init__(
        self,
        settings: DNAGenotekSettings | None = None,
        session: requests.Session | None = None,
    ) -> None:
        """Initialize DNAGenotekClient."""
        self._settings = settings
        self._session = session or requests.Session()
        self._headers: dict[str, str] = {}

    @classmethod
    def from_env(cls) -> DNAGenotekClient:
        """Build client from environment variables."""
        return cls(settings=DNAGenotekSettings.from_env())

    def _get_settings(self) -> DNAGenotekSettings:
        if self._settings is None:
            self._settings = DNAGenotekSettings.from_env()
        return self._settings

    def _authenticate(self) -> None:
        if self._headers:
            return
        token = self._create_token()
        self._headers = {
            "Accept": "application/json",
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
        }

    def _create_token(self) -> str:
        settings = self._get_settings()
        credentials = f"{settings.api_key}:".encode()
        return base64.b64encode(credentials).decode("ascii")

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        self._authenticate()
        settings = self._get_settings()
        url = f"{settings.base_url}{path}"
        response = self._session.get(
            url,
            headers=self._headers,
            params=params,
            timeout=settings.timeout,
        )
        response.raise_for_status()
        return response.json()

    def _post(self, path: str, body: dict[str, Any], params: dict[str, Any] | None = None) -> Any:
        self._authenticate()
        settings = self._get_settings()
        url = f"{settings.base_url}{path}"
        response = self._session.post(
            url,
            json=body,
            headers=self._headers,
            params=params,
            timeout=settings.timeout,
        )
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            logger.error(f"DNAGenotek API error: {exc}")
            logger.error(f"DNAGenotek API response: {response.text}")
            raise DNAGenotekAuthenticationError(f"DNAGenotek request failed: {exc}") from exc

    def get_status(self) -> dict[str, Any]:
        """Return API status."""
        return self._get("/api/v1/status")  # type: ignore[no-any-return]

    def create_order(self, order: CreateDNAGenotekAPIOrderRequest) -> DNAGenotekAPIOrder:
        """Create API order."""
        data = self._post("/api/v2/orders", order.model_dump(exclude_none=True))
        return _api_order_from_dict(data)

    def get_order(self, order_id: int) -> DNAGenotekAPIOrder:
        """Get API order."""
        data = self._get(f"/api/v2/orders/{order_id}")
        return _api_order_from_dict(data)

    def list_orders(self, params: DNAGenotekAPIListOrdersParams | None = None) -> list[DNAGenotekAPIOrder]:
        """List API orders (single page)."""
        request_params = params or DNAGenotekAPIListOrdersParams()
        orders = []
        raw_list = self._get("/api/v2/orders", params=request_params.model_dump())
        for data in raw_list:
            orders.append(_api_order_from_dict(data))
        return orders

    def list_all_orders(self, params: DNAGenotekAPIListOrdersParams | None = None) -> list[DNAGenotekAPIOrder]:
        """List all API orders across pages."""
        request_params = params or DNAGenotekAPIListOrdersParams()
        all_orders: list[DNAGenotekAPIOrder] = []

        current_page_orders = self.list_orders(request_params)
        all_orders.extend(current_page_orders)

        while current_page_orders and len(current_page_orders) == request_params.per_page:
            logger.info(f" * Page {request_params.page}: {len(current_page_orders)} orders")
            request_params.page += 1
            try:
                current_page_orders = self.list_orders(request_params)
                all_orders.extend(current_page_orders)
            except Exception as exc:
                logger.error(f"Error listing DNAGenotek orders: {exc}")
                break

        logger.info(f"DNA Genotek Orders: {len(all_orders)}")
        return all_orders
