"""DNA Genotek Models."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from enum import StrEnum
from functools import total_ordering
from typing import Any

from pydantic import BaseModel, ConfigDict


@total_ordering
class OrderedStrEnum(StrEnum):
    """Ordered String Enum class."""

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        members = list(self.__class__)
        return members.index(self) >= members.index(other)

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        members = list(self.__class__)
        return members.index(self) > members.index(other)

    def __le__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        members = list(self.__class__)
        return members.index(self) <= members.index(other)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        members = list(self.__class__)
        return members.index(self) < members.index(other)


def infer_carrier(tracking_number: str) -> str:
    """Infer the shipping carrier from a tracking number."""
    return "fedex" if len(tracking_number) == 12 else "usps"


def create_tracking_url(tracking_number: str) -> str | None:
    """Create a tracking URL."""
    if not tracking_number:
        return None

    carrier = infer_carrier(tracking_number)
    if carrier == "fedex":
        return f"https://www.fedex.com/fedextrack/?trknbr={tracking_number}"
    return f"https://tools.usps.com/go/TrackConfirmAction?tLabels={tracking_number}"


class DNAGenotekDestination(BaseModel):
    """DNA Genotek Destination model."""

    co_first_name: str
    co_last_name: str
    co_phone_number: str | None = None
    company: str | None = None
    address_1: str
    address_2: str | None = None
    city: str
    region: str
    postal_code: str
    country: str | None = None


class DNAGenotekOutboundOrder(BaseModel):
    """DNA Genotek Outbound Order model."""

    id: int | None = None
    model_config = ConfigDict(extra="allow")


class DNAGenotekReturnOrder(BaseModel):
    """DNA Genotek Return Order model."""

    id: int | None = None
    outbound_tracking: str | None = None
    shipped_on: datetime | None = None
    model_config = ConfigDict(extra="allow")


class DNAGenotekKit(BaseModel):
    """DNA Genotek Kit model."""

    barcode: str
    return_tracking: str
    pmi: str

    custom: dict[str, Any] | None = None
    outbound_order: DNAGenotekOutboundOrder | int | None = None
    return_order: DNAGenotekReturnOrder | None = None

    @property
    def return_tracking_url(self) -> str | None:
        """Return the return tracking URL."""
        if not self.return_tracking:
            return None
        return create_tracking_url(self.return_tracking)


class DNAGenotekLabel(BaseModel):
    """DNA Genotek Label model."""

    sample_id: str | None = None
    label_line_1: str | None = None
    label_line_2: str | None = None


class DNAGenotekOrderItem(BaseModel):
    """DNA Genotek Order Item model."""

    sku: str
    quantity: int


class DNAGenotekOrderStatus(OrderedStrEnum):
    """DNA Genotek Order Status model."""

    PENDING = "pending"
    FULFILLMENT = "fulfillment"
    SHIPPED = "shipped"
    ERROR = "error"

    @property
    def color(self) -> str:
        """Returns the Bootstrap color class for the kit status."""
        if self is DNAGenotekOrderStatus.SHIPPED:
            return "success"
        if self is DNAGenotekOrderStatus.FULFILLMENT:
            return "info"
        if self is DNAGenotekOrderStatus.PENDING:
            return "warning"
        if self is DNAGenotekOrderStatus.ERROR:
            return "danger"
        return "secondary"


class DNAGenotekAPIListOrdersParams(BaseModel):
    """DNA Genotek List Orders Params model."""

    created_after: str | None = None
    updated_after: str | None = None
    status: str | None = None
    secondary_id: str | None = None
    per_page: int = 100
    page: int = 1


class BaseDNAGenotekOrder(BaseModel):
    """Base DNA Genotek Order model."""

    destination: DNAGenotekDestination
    items: list[DNAGenotekOrderItem]
    kits: list[DNAGenotekKit] | None = None
    labels: list[DNAGenotekLabel] | None = None

    customer_id: str | None = None
    outbound_tracking: str | None = None
    fulfillment_id: str | None = None
    order_type: str | None = None
    service_level: str | None = None
    error_detail: str | None = None
    status: DNAGenotekOrderStatus = DNAGenotekOrderStatus.PENDING

    created_on: datetime | None = None
    expected_shipped_on: datetime | None = None
    shipped_on: datetime | None = None
    updated_on: datetime | None = None


class CreateDNAGenotekAPIOrderRequest(BaseDNAGenotekOrder):
    """Create DNA Genotek API Order Request model."""


class DNAGenotekAPIOrder(BaseDNAGenotekOrder):
    """DNA Genotek API Order model."""

    id: int
