"""Endpoint definitions shared by the sync and the async client.

Every endpoint is written once in :class:`Endpoints`. A method only builds
the payload and hands it to ``self._call``: the sync client returns the
result, the async client returns an awaitable. The generic parameter ``R``
keeps the return types right for type checkers and IDEs.
"""

from __future__ import annotations

import json
from contextlib import suppress
from collections.abc import Iterable, Mapping
from datetime import date, datetime, time
from typing import Any, Generic, TypeVar

from ._version import __version__
from .exceptions import TransportError, error_for
from .models import (
    MAX_SMS_PER_REQUEST,
    Message,
    _fmt_date,
    _fmt_period,
    _fmt_time,
    drop_none,
)

R = TypeVar("R")

DEFAULT_BASE_URL = "https://restapi.sempico.solutions"
DEFAULT_TIMEOUT = 30.0
USER_AGENT = f"gatum-rest-py/{__version__}"

Number = str | int


def normalize_base_url(base_url: str) -> str:
    """Accept ``https://host``, ``https://host/`` or ``https://host/v1``."""
    url = base_url.strip().rstrip("/")
    if not url.endswith("/v1"):
        url += "/v1"
    return url


def numbers_list(numbers: Iterable[Number] | Number) -> list[str]:
    if isinstance(numbers, (str, int)):
        numbers = [numbers]
    return [str(n) for n in numbers]


def parse_response(status_code: int, headers: Mapping[str, str], content: bytes) -> Any:
    """Return ``data`` of a successful answer, raise :class:`APIError` otherwise."""
    try:
        body = json.loads(content) if content else None
    except ValueError as exc:
        raise TransportError(
            f"HTTP {status_code}: the answer is not JSON: {content[:200]!r}"
        ) from exc

    if isinstance(body, dict) and body.get("status") is True and status_code < 400:
        return body.get("data")

    retry_after: float | None = None
    raw_retry = headers.get("retry-after")
    if raw_retry:
        with suppress(ValueError):
            retry_after = float(raw_retry)
    # An error is normally an HTTP 4xx. If the HTTP status is 2xx but the body
    # says "status": false, trust the error_code of the body.
    code = status_code
    if code < 400:
        code = int(body.get("error_code", 400)) if isinstance(body, dict) else 400
    raise error_for(code, body, retry_after)


def plan_send(messages: Iterable[Message]) -> list[list[dict[str, Any]]]:
    """Split packages into request bodies of at most 100 SMS each.

    A package with more numbers than fit is split into several packages
    with the same text, so the caller never has to count.
    """
    requests: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    room = MAX_SMS_PER_REQUEST
    for message in messages:
        payload = message.to_payload()
        numbers = payload["number"]
        if not numbers:
            continue
        while numbers:
            if room == 0:
                requests.append(current)
                current, room = [], MAX_SMS_PER_REQUEST
            take, numbers = numbers[:room], numbers[room:]
            current.append({**payload, "number": take})
            room -= len(take)
    if current:
        requests.append(current)
    return requests


class Endpoints(Generic[R]):
    """All REST API methods. Subclasses implement :meth:`_call`."""

    def _call(
        self, method: str, path: str, payload: Any = None, *, auth: bool = True
    ) -> R:  # pragma: no cover - implemented by the clients
        raise NotImplementedError

    # --- Account ----------------------------------------------------------

    def me(self) -> R:
        """Profile and balance of the account.

        Rate limit: 1 request per 15 minutes per IP.
        """
        return self._call("GET", "/me")

    def register(
        self,
        login: str,
        password: str,
        name: str,
        phone: str,
        email: str,
        *,
        company_name: str | None = None,
        skype: str | None = None,
    ) -> R:
        """Register a new customer. Rate limit: 2 requests per hour per IP."""
        payload = drop_none(
            {
                "login": login,
                "password": password,
                "name": name,
                "phone": phone,
                "email": email,
                "company_name": company_name,
                "skype": skype,
            }
        )
        return self._call("POST", "/register", payload, auth=False)

    # --- Statistics -------------------------------------------------------

    def sms_full_data(
        self,
        *,
        mcc: int | None = None,
        mnc: int | None = None,
        sender_id: str | None = None,
        phone: Iterable[Number] | None = None,
        id_base: Iterable[int] | None = None,
        time_period: tuple[datetime, datetime] | str | None = None,
        type_sms: str | None = None,
        state: Iterable[str] | None = None,
        id_state: Iterable[int] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> R:
        """Data of the SMS sent in the last few days.

        ``time_period`` is a ``(start, end)`` tuple of datetimes or a
        ``'YYYY-MM-DD HH:MM:SS - YYYY-MM-DD HH:MM:SS'`` string.
        Rate limit: 1 request per 15 minutes per IP.
        """
        payload = drop_none(
            {
                "MCC": mcc,
                "MNC": mnc,
                "senderID": sender_id,
                "phone": numbers_list(phone) if phone is not None else None,
                "id_base": list(id_base) if id_base is not None else None,
                "time_period": _fmt_period(time_period),
                "type_sms": type_sms,
                "state": list(state) if state is not None else None,
                "id_state": list(id_state) if id_state is not None else None,
                "limit": limit,
                "offset": offset,
            }
        )
        return self._call("POST", "/sms-full-data", payload)

    def stat(
        self,
        *,
        groups_choose: Iterable[str] | None = None,
        destination: Iterable[Any] | None = None,
        date_range: tuple[datetime, datetime] | str | None = None,
        type_sms: Iterable[str] | None = None,
        id_name_delivery: int | None = None,
    ) -> R:
        """General statistics. Rate limit: 1 request per 15 minutes per IP."""
        payload = drop_none(
            {
                "groups_choose": list(groups_choose) if groups_choose is not None else None,
                "destination": list(destination) if destination is not None else None,
                "date_range": _fmt_period(date_range),
                "type_sms": list(type_sms) if type_sms is not None else None,
                "id_name_delivery": id_name_delivery,
            }
        )
        return self._call("POST", "/stat", payload)

    # --- Groups of numbers ------------------------------------------------

    def groups(
        self, *, id_group: int | None = None, limit: int | None = None, offset: int | None = None
    ) -> R:
        """List the groups (``limit`` is 100 at most, ``offset`` is a page number)."""
        payload = drop_none({"id_group": id_group, "limit": limit, "offset": offset})
        return self._call("POST", "/group", payload)

    def create_group(
        self,
        name: str,
        *,
        time_birth: time | str | None = None,
        originator_birth: str | None = None,
        text_birth: str | None = None,
        on_birth: bool | None = None,
    ) -> R:
        """Create a group. ``#first_name#`` in ``text_birth`` is replaced by the contact's name."""
        birth_time = time_birth.strftime("%H:%M") if isinstance(time_birth, time) else time_birth
        payload = drop_none(
            {
                "name_group": name,
                "time_birth": birth_time,
                "originator_birth": originator_birth,
                "text_birth": text_birth,
                "on_birth": on_birth,
            }
        )
        return self._call("POST", "/group-create", payload)

    def delete_groups(self, ids: Iterable[int] | int) -> R:
        """Delete groups and all their numbers. This cannot be undone."""
        ids = [ids] if isinstance(ids, int) else list(ids)
        return self._call("POST", "/group-delete", {"id_group": ids})

    def group_add_numbers(
        self, id_group: int, numbers: Iterable[Number | Mapping[str, Any]]
    ) -> R:
        """Add numbers to a group.

        Every item is a phone number or a dict with ``number`` and optional
        ``name``, ``surname``, ``patronymic``, ``date_birth``, ``male``
        (``'m'``/``'f'``) and ``note_1`` ... ``note_10``.
        """
        items = []
        for item in numbers:
            if isinstance(item, Mapping):
                entry = {k: v for k, v in item.items() if v is not None}
                entry["number"] = str(entry["number"])
                if isinstance(entry.get("date_birth"), date):
                    entry["date_birth"] = _fmt_date(entry["date_birth"])
            else:
                entry = {"number": str(item)}
            items.append(entry)
        return self._call("POST", "/group-number-add", {"id_group": id_group, "numbers": items})

    def group_search_numbers(self, id_group: int, numbers: Iterable[Number]) -> R:
        return self._call(
            "POST", "/group-number-search", {"id_group": id_group, "numbers": numbers_list(numbers)}
        )

    def group_delete_numbers(self, id_group: int, numbers: Iterable[Number]) -> R:
        return self._call(
            "POST", "/group-number-delete", {"id_group": id_group, "numbers": numbers_list(numbers)}
        )

    def send_bulk(
        self,
        sender_id: str,
        text: str,
        id_group: Iterable[int] | int,
        *,
        id_group_excluded: Iterable[int] | None = None,
        phone: Iterable[Number] | None = None,
        date_start: date | str | None = None,
        time_start: time | str | None = None,
        time_stop: time | str | None = None,
    ) -> R:
        """Campaign to the numbers of groups.

        With ``date_start``/``time_start``/``time_stop`` the SMS are sent
        gradually over this period; without them, at once.
        """
        id_group = [id_group] if isinstance(id_group, int) else list(id_group)
        payload = drop_none(
            {
                "senderID": sender_id,
                "text": text,
                "id_group": id_group,
                "id_group_excluded": list(id_group_excluded) if id_group_excluded is not None else None,
                "phone": numbers_list(phone) if phone is not None else None,
                "dateStart": _fmt_date(date_start),
                "timeStart": _fmt_time(time_start),
                "timeStop": _fmt_time(time_stop),
            }
        )
        return self._call("POST", "/send-bulk", payload)

    # --- Black list -------------------------------------------------------

    def blacklist_add(self, numbers: Iterable[Number]) -> R:
        """Add up to 1000 numbers to the personal black list."""
        return self._call("POST", "/black-list-add", {"numbers": numbers_list(numbers)})

    def blacklist_search(self, numbers: Iterable[Number]) -> R:
        return self._call("POST", "/black-list-search", {"numbers": numbers_list(numbers)})

    def blacklist_delete(self, numbers: Iterable[Number]) -> R:
        return self._call("POST", "/black-list-delete", {"numbers": numbers_list(numbers)})

    # --- Tools ------------------------------------------------------------

    def replacement(self, numbers: Iterable[Number] | Number, sender_id: str, text: str) -> R:
        """Show how the text and sender ID would be replaced for each number, without sending."""
        payload = [{"number": numbers_list(numbers), "senderID": sender_id, "text": text}]
        return self._call("POST", "/replacement", payload)

    # --- Prices -----------------------------------------------------------

    def product_price(
        self, *, iso: str | None = None, mcc: str | int | None = None, mnc: str | int | None = None
    ) -> R:
        return self._call("POST", "/product-price", _price_filter(iso, mcc, mnc))

    def account_price(
        self, *, iso: str | None = None, mcc: str | int | None = None, mnc: str | int | None = None
    ) -> R:
        return self._call("POST", "/account-price", _price_filter(iso, mcc, mnc))

    def country_price(self, *, iso: str | None = None, mcc: str | int | None = None) -> R:
        return self._call("POST", "/country-price", _price_filter(iso, mcc, None))

    def country_by_continent(self) -> R:
        return self._call("POST", "/country-by-continent", {})


def _price_filter(iso: str | None, mcc: str | int | None, mnc: str | int | None) -> dict[str, Any]:
    if mnc is not None and mcc is None:
        raise ValueError("mnc requires mcc")
    return drop_none(
        {
            "ISO": iso,
            "MCC": str(mcc) if mcc is not None else None,
            "MNC": str(mnc) if mnc is not None else None,
        }
    )


def env_kwargs(prefix: str = "GATUM_") -> dict[str, Any]:
    """Client arguments from environment variables.

    ``GATUM_ACCESS_TOKEN``, ``GATUM_USERNAME``, ``GATUM_PASSWORD``,
    ``GATUM_BASE_URL``, ``GATUM_TIMEOUT``.
    """
    import os

    env = {k: os.environ.get(prefix + k.upper()) for k in
           ("access_token", "username", "password", "base_url", "timeout")}
    kwargs: dict[str, Any] = {k: v for k, v in env.items() if v}
    if "timeout" in kwargs:
        kwargs["timeout"] = float(kwargs["timeout"])
    return kwargs
