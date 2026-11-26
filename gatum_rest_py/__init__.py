"""Python SDK for the Gatum / Sempico REST API: SMS, HLR, MNP, groups, black list, prices, DLR."""

from typing import Any

from ._version import __version__
from .async_client import AsyncGatumClient
from .client import GatumClient
from .dlr import confirm, parse_dlr
from .exceptions import (
    APIError,
    AuthenticationError,
    BadRequestError,
    GatumError,
    PermissionDeniedError,
    RateLimitError,
    TransportError,
)
from .models import AccessToken, DeliveryReport, Message, SendResult

__all__ = [
    "__version__",
    "GatumClient",
    "AsyncGatumClient",
    "Message",
    "SendResult",
    "AccessToken",
    "DeliveryReport",
    "parse_dlr",
    "confirm",
    "GatumError",
    "TransportError",
    "APIError",
    "BadRequestError",
    "AuthenticationError",
    "PermissionDeniedError",
    "RateLimitError",
    "GatumRESTAPI",
]


def __getattr__(name: str) -> Any:
    # The deprecated 1.x client needs `requests`; import it only when used.
    if name == "GatumRESTAPI":
        from .GatumRESTAPI import GatumRESTAPI

        return GatumRESTAPI
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
