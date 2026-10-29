"""dnagenotek-python client."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from altissimo.dnagenotek.client import DNAGenotekClient, DNAGenotekSettings
from altissimo.dnagenotek.exceptions import (
    DNAGenotekAuthenticationError,
    DNAGenotekOrderNotFoundError,
)
from altissimo.dnagenotek.models import (
    BaseDNAGenotekOrder,
    CreateDNAGenotekAPIOrderRequest,
    DNAGenotekAPIListOrdersParams,
    DNAGenotekAPIOrder,
    DNAGenotekDestination,
    DNAGenotekKit,
    DNAGenotekLabel,
    DNAGenotekOrderItem,
    DNAGenotekOrderStatus,
    DNAGenotekOutboundOrder,
    DNAGenotekReturnOrder,
    OrderedStrEnum,
    create_tracking_url,
    infer_carrier,
)

try:
    __version__ = version("dnagenotek-python")
except PackageNotFoundError:  # pragma: no cover — editable install without metadata
    __version__ = "0.1.0"

__all__ = [
    "BaseDNAGenotekOrder",
    "CreateDNAGenotekAPIOrderRequest",
    "DNAGenotekAPIListOrdersParams",
    "DNAGenotekAPIOrder",
    "DNAGenotekAuthenticationError",
    "DNAGenotekClient",
    "DNAGenotekDestination",
    "DNAGenotekKit",
    "DNAGenotekLabel",
    "DNAGenotekOrderItem",
    "DNAGenotekOrderNotFoundError",
    "DNAGenotekOrderStatus",
    "DNAGenotekOutboundOrder",
    "DNAGenotekReturnOrder",
    "DNAGenotekSettings",
    "OrderedStrEnum",
    "__version__",
    "create_tracking_url",
    "infer_carrier",
]
