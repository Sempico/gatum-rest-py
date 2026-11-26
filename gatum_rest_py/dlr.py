"""Delivery reports (DLR) webhook: framework-independent part.

The API sends a ``POST`` with a JSON array of reports to the ``callback_url``
of ``/send`` (or the URL set in the dashboard). If a security key is set for
the account, it comes in the ``API_KEY`` header. HTTP 200 means the
reports were received; in the confirmation mode the answer must be the JSON
array of the confirmed ``id_state``. A report is sent no more than twice.

The framework integrations in :mod:`gatum_rest_py.integrations` are thin
wrappers around :func:`process_dlr`.
"""

from __future__ import annotations

import hmac
import inspect
from collections.abc import Awaitable, Callable, Iterable, Sequence
from typing import Any

from .exceptions import GatumError
from .models import DeliveryReport

__all__ = [
    "API_KEY_HEADER",
    "DLRHandler",
    "InvalidDLRRequest",
    "parse_dlr",
    "confirm",
    "check_api_key",
    "process_dlr",
    "aprocess_dlr",
]

API_KEY_HEADER = "API_KEY"

HandlerResult = Iterable[DeliveryReport | int] | None

#: Callback that gets the parsed reports. It may return the reports (or
#: their ``id_state``) to confirm; ``None`` confirms all of them.
DLRHandler = Callable[[list[DeliveryReport]], HandlerResult | Awaitable[HandlerResult]]


class InvalidDLRRequest(GatumError):
    """The webhook request is not a valid DLR request (wrong key or body)."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        self.status_code = status_code
        super().__init__(message)


def parse_dlr(body: Any) -> list[DeliveryReport]:
    """Turn the decoded JSON body of a webhook request into reports."""
    if isinstance(body, dict):  # be lenient: a single report
        body = [body]
    if not isinstance(body, list):
        raise InvalidDLRRequest("DLR body must be a JSON array")
    try:
        return [DeliveryReport.from_dict(item) for item in body]
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidDLRRequest(f"Malformed DLR item: {exc}") from exc


def confirm(reports: Iterable[DeliveryReport | int]) -> list[int]:
    """The answer body that confirms these reports: a list of ``id_state``."""
    return [r.id_state if isinstance(r, DeliveryReport) else int(r) for r in reports]


def check_api_key(received: str | None, expected: str | None) -> None:
    """Raise :class:`InvalidDLRRequest` (403) if the ``API_KEY`` header does not match.

    Does nothing when ``expected`` is empty (no key set for the account).
    """
    if not expected:
        return
    if not received or not hmac.compare_digest(received.encode(), expected.encode()):
        raise InvalidDLRRequest("Invalid API_KEY", status_code=403)


def _prepare(body: Any, api_key: str | None, expected_api_key: str | None) -> list[DeliveryReport]:
    check_api_key(api_key, expected_api_key)
    return parse_dlr(body)


def _answer(reports: Sequence[DeliveryReport], returned: Any) -> list[int]:
    return confirm(reports if returned is None else returned)


def process_dlr(
    body: Any,
    handler: DLRHandler,
    *,
    api_key: str | None = None,
    expected_api_key: str | None = None,
) -> list[int]:
    """Check the key, parse the body, call ``handler``, return the answer body."""
    reports = _prepare(body, api_key, expected_api_key)
    returned = handler(reports)
    if inspect.isawaitable(returned):
        if inspect.iscoroutine(returned):
            returned.close()
        raise TypeError("Use aprocess_dlr() with an async handler")
    return _answer(reports, returned)


async def aprocess_dlr(
    body: Any,
    handler: DLRHandler,
    *,
    api_key: str | None = None,
    expected_api_key: str | None = None,
) -> list[int]:
    """Same as :func:`process_dlr`; ``handler`` may be sync or async."""
    reports = _prepare(body, api_key, expected_api_key)
    returned = handler(reports)
    if inspect.isawaitable(returned):
        returned = await returned
    return _answer(reports, returned)
