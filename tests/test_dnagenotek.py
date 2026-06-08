"""Unit tests for DNA Genotek client, settings, and models."""

from __future__ import annotations

import base64
from unittest.mock import MagicMock, patch

import pytest
import requests

from altissimo.dnagenotek import (
    CreateDNAGenotekAPIOrderRequest,
    DNAGenotekAPIListOrdersParams,
    DNAGenotekAPIOrder,
    DNAGenotekAuthenticationError,
    DNAGenotekClient,
    DNAGenotekDestination,
    DNAGenotekKit,
    DNAGenotekOrderItem,
    DNAGenotekOrderStatus,
    DNAGenotekSettings,
)


def test_dnagenotek_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test DNAGenotekSettings environment variables parsing."""
    monkeypatch.delenv("DNAGENOTEK_API_KEY", raising=False)
    monkeypatch.delenv("DNAGENOTEK_BASE_URL", raising=False)

    with pytest.raises(ValueError, match="DNAGENOTEK_API_KEY is not set"):
        DNAGenotekSettings.from_env()

    monkeypatch.setenv("DNAGENOTEK_API_KEY", "test-key")
    with pytest.raises(ValueError, match="DNAGENOTEK_BASE_URL is not set"):
        DNAGenotekSettings.from_env()

    monkeypatch.setenv("DNAGENOTEK_BASE_URL", "https://api.sofia.com")
    settings = DNAGenotekSettings.from_env()
    assert settings.api_key == "test-key"
    assert settings.base_url == "https://api.sofia.com"
    assert settings.timeout == 10

    # Custom env var names
    monkeypatch.setenv("CUSTOM_API_KEY", "c-key")
    monkeypatch.setenv("CUSTOM_BASE_URL", "c-url")
    settings_custom = DNAGenotekSettings.from_env(
        api_key_env="CUSTOM_API_KEY",
        base_url_env="CUSTOM_BASE_URL",
    )
    assert settings_custom.api_key == "c-key"
    assert settings_custom.base_url == "c-url"


def test_ordered_str_enum() -> None:
    """Test the comparison behavior of OrderedStrEnum."""
    assert DNAGenotekOrderStatus.PENDING < DNAGenotekOrderStatus.FULFILLMENT
    assert DNAGenotekOrderStatus.FULFILLMENT < DNAGenotekOrderStatus.SHIPPED
    assert DNAGenotekOrderStatus.PENDING <= DNAGenotekOrderStatus.SHIPPED
    assert DNAGenotekOrderStatus.SHIPPED > DNAGenotekOrderStatus.FULFILLMENT
    assert DNAGenotekOrderStatus.SHIPPED >= DNAGenotekOrderStatus.PENDING
    assert DNAGenotekOrderStatus.PENDING.value == "pending"


def test_tracking_urls() -> None:
    """Test infer_carrier and create_tracking_url helpers."""
    # 12 digits -> FedEx
    kit_fedex = DNAGenotekKit(barcode="B1", return_tracking="123456789012", pmi="P1")
    assert kit_fedex.return_tracking_url == "https://www.fedex.com/fedextrack/?trknbr=123456789012"

    # Other digits -> USPS
    kit_usps = DNAGenotekKit(barcode="B1", return_tracking="9400111899562234567890", pmi="P1")
    assert kit_usps.return_tracking_url == "https://tools.usps.com/go/TrackConfirmAction?tLabels=9400111899562234567890"

    # Empty
    kit_empty = DNAGenotekKit(barcode="B1", return_tracking="", pmi="P1")
    assert kit_empty.return_tracking_url is None


def test_status_color() -> None:
    """Test DNAGenotekOrderStatus Bootstrap color mapping."""
    assert DNAGenotekOrderStatus.PENDING.color == "warning"
    assert DNAGenotekOrderStatus.FULFILLMENT.color == "info"
    assert DNAGenotekOrderStatus.SHIPPED.color == "success"
    assert DNAGenotekOrderStatus.ERROR.color == "danger"


@patch("requests.Session")
def test_client_authentication_headers(mock_session_cls: MagicMock) -> None:
    """Test headers construction with basic auth token."""
    settings = DNAGenotekSettings(api_key="api-key-123", base_url="https://sofia.com")
    client = DNAGenotekClient(settings=settings)

    client._authenticate()
    headers = client._headers
    assert headers["Accept"] == "application/json"
    assert headers["Content-Type"] == "application/json"
    assert headers["Authorization"].startswith("Basic ")

    # Decoded credentials check
    encoded_creds = headers["Authorization"].split(" ")[1]
    decoded = base64.b64decode(encoded_creds.encode()).decode()
    assert decoded == "api-key-123:"


def test_get_status() -> None:
    """Test get_status method."""
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "operational"}
    mock_session.get.return_value = mock_response

    settings = DNAGenotekSettings(api_key="key", base_url="https://api.com")
    client = DNAGenotekClient(settings=settings, session=mock_session)

    res = client.get_status()
    assert res == {"status": "operational"}
    mock_session.get.assert_called_once_with(
        "https://api.com/api/v1/status",
        headers=client._headers,
        params=None,
        timeout=10,
    )


def test_create_order() -> None:
    """Test order creation submission and parsing."""
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": 987,
        "destination": {
            "co_first_name": "John",
            "co_last_name": "Doe",
            "address_1": "1 Main St",
            "city": "Boston",
            "region": "MA",
            "postal_code": "02111",
        },
        "items": [{"sku": "SKU-1", "quantity": 2}],
        "kits": None,
        "labels": None,
        "customer_id": "cust-abc",
        "status": "pending",
    }
    mock_session.post.return_value = mock_response

    settings = DNAGenotekSettings(api_key="key", base_url="https://api.com")
    client = DNAGenotekClient(settings=settings, session=mock_session)

    req = CreateDNAGenotekAPIOrderRequest(
        destination=DNAGenotekDestination(
            co_first_name="John",
            co_last_name="Doe",
            address_1="1 Main St",
            city="Boston",
            region="MA",
            postal_code="02111",
        ),
        items=[DNAGenotekOrderItem(sku="SKU-1", quantity=2)],
        customer_id="cust-abc",
    )

    order = client.create_order(req)
    assert isinstance(order, DNAGenotekAPIOrder)
    assert order.id == 987
    assert order.destination.co_first_name == "John"
    assert order.status == DNAGenotekOrderStatus.PENDING
    mock_session.post.assert_called_once()


def test_get_order() -> None:
    """Test getting order by ID."""
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": 456,
        "destination": {
            "co_first_name": "John",
            "co_last_name": "Doe",
            "address_1": "1 Main St",
            "city": "Boston",
            "region": "MA",
            "postal_code": "02111",
        },
        "items": [],
        "kits": None,
        "labels": None,
    }
    mock_session.get.return_value = mock_response

    settings = DNAGenotekSettings(api_key="key", base_url="https://api.com")
    client = DNAGenotekClient(settings=settings, session=mock_session)

    order = client.get_order(456)
    assert order.id == 456
    mock_session.get.assert_called_once_with(
        "https://api.com/api/v2/orders/456",
        headers=client._headers,
        params=None,
        timeout=10,
    )


def test_list_orders() -> None:
    """Test list_orders method returning single page."""
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "id": 1,
            "destination": {
                "co_first_name": "A",
                "co_last_name": "B",
                "address_1": "1 Main St",
                "city": "Boston",
                "region": "MA",
                "postal_code": "02111",
            },
            "items": [],
            "kits": None,
            "labels": None,
        }
    ]
    mock_session.get.return_value = mock_response

    settings = DNAGenotekSettings(api_key="key", base_url="https://api.com")
    client = DNAGenotekClient(settings=settings, session=mock_session)

    params = DNAGenotekAPIListOrdersParams(per_page=10, page=2)
    orders = client.list_orders(params)
    assert len(orders) == 1
    assert orders[0].id == 1
    mock_session.get.assert_called_once_with(
        "https://api.com/api/v2/orders",
        headers=client._headers,
        params={
            "created_after": None,
            "updated_after": None,
            "status": None,
            "secondary_id": None,
            "per_page": 10,
            "page": 2,
        },
        timeout=10,
    )


def test_list_all_orders_pagination() -> None:
    """Test list_all_orders auto-paginates across multiple pages."""
    mock_session = MagicMock()

    # Define mock response data for page 1 and page 2 (empty page 2 to terminate)
    order_p1_1 = {
        "id": 100,
        "destination": {
            "co_first_name": "A",
            "co_last_name": "B",
            "address_1": "1 Main St",
            "city": "Boston",
            "region": "MA",
            "postal_code": "02111",
        },
        "items": [],
        "kits": None,
        "labels": None,
    }
    order_p1_2 = {
        "id": 101,
        "destination": {
            "co_first_name": "C",
            "co_last_name": "D",
            "address_1": "2 Main St",
            "city": "Boston",
            "region": "MA",
            "postal_code": "02111",
        },
        "items": [],
        "kits": None,
        "labels": None,
    }

    mock_res_p1 = MagicMock()
    mock_res_p1.status_code = 200
    mock_res_p1.json.return_value = [order_p1_1, order_p1_2]  # per_page = 2

    mock_res_p2 = MagicMock()
    mock_res_p2.status_code = 200
    mock_res_p2.json.return_value = []

    mock_session.get.side_effect = [mock_res_p1, mock_res_p2]

    settings = DNAGenotekSettings(api_key="key", base_url="https://api.com")
    client = DNAGenotekClient(settings=settings, session=mock_session)

    params = DNAGenotekAPIListOrdersParams(per_page=2, page=1)
    all_orders = client.list_all_orders(params)

    assert len(all_orders) == 2
    assert all_orders[0].id == 100
    assert all_orders[1].id == 101
    assert mock_session.get.call_count == 2


def test_client_post_request_error() -> None:
    """Test client post raises DNAGenotekAuthenticationError on HTTPError."""
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    mock_response.raise_for_status.side_effect = requests.exceptions.RequestException(
        "Unauthorized", response=mock_response
    )
    mock_session.post.return_value = mock_response

    settings = DNAGenotekSettings(api_key="key", base_url="https://api.com")
    client = DNAGenotekClient(settings=settings, session=mock_session)

    with pytest.raises(DNAGenotekAuthenticationError, match="DNAGenotek request failed:"):
        client.create_order(
            CreateDNAGenotekAPIOrderRequest(
                destination=DNAGenotekDestination(
                    co_first_name="A", co_last_name="B", address_1="X", city="Y", region="Z", postal_code="0"
                ),
                items=[],
            )
        )
