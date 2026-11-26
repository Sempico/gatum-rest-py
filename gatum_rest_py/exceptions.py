"""Exceptions raised by the Gatum REST API clients."""

from __future__ import annotations

from typing import Any

__all__ = [
    "GatumError",
    "TransportError",
    "APIError",
    "BadRequestError",
    "AuthenticationError",
    "PermissionDeniedError",
    "RateLimitError",
]


class GatumError(Exception):
    """Base class for every error raised by this library."""


class TransportError(GatumError):
    """The request did not reach the API, or the answer was not valid JSON."""


class APIError(GatumError):
    """The API answered with ``{"status": false, ...}``.

    Attributes:
        status_code: HTTP status of the response.
        errors: The ``errors`` field of the response, either a string or a
            mapping of field name to a list of messages.
        body: The whole decoded JSON body.
    """

    def __init__(self, status_code: int, errors: Any, body: Any = None) -> None:
        self.status_code = status_code
        self.errors = errors
        self.body = body
        super().__init__(f"[{status_code}] {self.message}")

    @property
    def message(self) -> str:
        """``errors`` flattened into one readable line."""
        if isinstance(self.errors, dict):
            parts = []
            for field, messages in self.errors.items():
                if isinstance(messages, (list, tuple)):
                    messages = "; ".join(str(m) for m in messages)
                parts.append(f"{field}: {messages}")
            return ", ".join(parts)
        return str(self.errors)


class BadRequestError(APIError):
    """HTTP 400: the request or its data was not accepted."""


class AuthenticationError(APIError):
    """HTTP 401: the access token is missing, wrong, expired or logged out."""


class PermissionDeniedError(APIError):
    """HTTP 403: IP not in the white list, or REST API not enabled for the account."""


class RateLimitError(APIError):
    """HTTP 429: the rate limit was exceeded.

    Attributes:
        retry_after: Seconds to wait before the next request, from the
            ``Retry-After`` header (``None`` if the header is missing).
    """

    def __init__(
        self, status_code: int, errors: Any, body: Any = None, retry_after: float | None = None
    ) -> None:
        self.retry_after = retry_after
        super().__init__(status_code, errors, body)


_BY_STATUS: dict[int, type[APIError]] = {
    400: BadRequestError,
    401: AuthenticationError,
    403: PermissionDeniedError,
}


def error_for(status_code: int, body: Any, retry_after: float | None = None) -> APIError:
    """Build the matching :class:`APIError` subclass for an error response."""
    errors = body.get("errors") if isinstance(body, dict) else body
    if status_code == 429:
        return RateLimitError(status_code, errors, body, retry_after)
    return _BY_STATUS.get(status_code, APIError)(status_code, errors, body)
