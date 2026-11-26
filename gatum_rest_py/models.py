"""Typed request and response objects."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Any, Literal

__all__ = [
    "SmsType",
    "Message",
    "SendResult",
    "AccessToken",
    "DeliveryReport",
]

SmsType = Literal["sms", "flashsms", "wappush", "vcard", "hlr", "mnp"]

#: Maximum number of SMS (phone numbers in all packages) in one ``/send`` request.
MAX_SMS_PER_REQUEST = 100


def _fmt_date(value: date | str | None) -> str | None:
    if isinstance(value, datetime):
        value = value.date()
    return value.isoformat() if isinstance(value, date) else value


def _fmt_time(value: time | str | None) -> str | None:
    return value.strftime("%H:%M:%S") if isinstance(value, time) else value


def _fmt_period(value: tuple[datetime, datetime] | str | None) -> str | None:
    """``(start, end)`` -> ``'YYYY-MM-DD HH:MM:SS - YYYY-MM-DD HH:MM:SS'``."""
    if value is None or isinstance(value, str):
        return value
    start, end = value
    return f"{start:%Y-%m-%d %H:%M:%S} - {end:%Y-%m-%d %H:%M:%S}"


def drop_none(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in payload.items() if v is not None}


@dataclass
class Message:
    """One package of ``/send``: one text for a list of numbers.

    ``begin_date`` / ``begin_time`` accept :class:`datetime.date` /
    :class:`datetime.time` objects or ready strings (``YYYY-MM-DD``,
    ``HH:MM[:SS]``, GMT+0).
    """

    numbers: Iterable[str | int]
    sender_id: str
    text: str
    type: SmsType = "sms"
    begin_date: date | str | None = None
    begin_time: time | str | None = None
    lifetime: int | None = None
    callback_url: str | None = None
    delivery: bool = True
    campaign: str | None = None
    shortener: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.numbers, (str, int)):
            self.numbers = [self.numbers]
        self.numbers = [str(n) for n in self.numbers]

    def to_payload(self) -> dict[str, Any]:
        return drop_none(
            {
                "number": list(self.numbers),
                "senderID": self.sender_id,
                "text": self.text,
                "type": self.type,
                "beginDate": _fmt_date(self.begin_date),
                "beginTime": _fmt_time(self.begin_time),
                "lifetime": self.lifetime,
                "callback_url": self.callback_url,
                "delivery": self.delivery,
                "campaign": self.campaign,
                "shortener": self.shortener,
            }
        )


@dataclass
class SendResult:
    """Answer of ``/send``.

    The API accepts every number on its own: some may be created while
    others fail (for example ``phone_in_black_list``), and the HTTP status is
    still 200. This object splits the answer into the two parts.

    Attributes:
        ids: phone -> list of ``id_state`` (one per SMS part).
        failed: phone -> error code (see the API docs for the list).
        raw: the ``data`` of all responses, merged.
    """

    ids: dict[str, list[int]] = field(default_factory=dict)
    failed: dict[str, str] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_data(cls, data: Mapping[str, Any]) -> SendResult:
        result = cls()
        result.merge(data)
        return result

    def merge(self, data: Mapping[str, Any]) -> None:
        for phone, items in data.items():
            self.raw[phone] = items
            for item in items or []:
                if "error" in item:
                    self.failed[phone] = item["error"]
                elif "id_state" in item:
                    self.ids.setdefault(phone, []).append(item["id_state"])

    @property
    def ok(self) -> bool:
        """``True`` when no number failed."""
        return not self.failed


@dataclass(frozen=True)
class AccessToken:
    token: str
    expires_at: datetime | None

    @classmethod
    def from_data(cls, data: Mapping[str, Any]) -> AccessToken:
        return cls(token=data["access_token"], expires_at=_parse_expires(data.get("expires_at")))

    def is_expired(self, leeway: float = 60.0) -> bool:
        if self.expires_at is None:
            return False
        now = datetime.now(self.expires_at.tzinfo)
        return (self.expires_at - now).total_seconds() <= leeway


def _parse_expires(value: Any) -> datetime | None:
    # Older API versions returned a UNIX timestamp, current ones a
    # 'YYYY-MM-DD HH:MM:SS' string.
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value)
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


@dataclass(frozen=True)
class DeliveryReport:
    """One item of a DLR webhook request (the state of one SMS part)."""

    id_state: int
    phone: str
    state: str
    originator: str | None = None
    type_sms: str | None = None
    text_sms: str | None = None
    num_parts: int | None = None
    part_no: int | None = None
    time: str | None = None
    price: float | None = None
    error: int | None = None
    hlr: dict[str, Any] | None = None
    raw: dict[str, Any] = field(default_factory=dict, compare=False, repr=False)

    @classmethod
    def from_dict(cls, item: Mapping[str, Any]) -> DeliveryReport:
        return cls(
            id_state=int(item["id_state"]),
            phone=str(item.get("phone", "")),
            state=str(item.get("state", "")),
            originator=item.get("originator"),
            type_sms=item.get("type_sms"),
            text_sms=item.get("text_sms"),
            num_parts=item.get("num_parts"),
            part_no=item.get("part_no"),
            time=item.get("time"),
            price=item.get("price"),
            error=item.get("error"),
            hlr=item.get("hlr"),
            raw=dict(item),
        )

    @property
    def delivered(self) -> bool:
        return self.state == "DELIVRD"

    @property
    def final(self) -> bool:
        """``True`` if the state will not change any more."""
        return self.state in {"DELIVRD", "UNDELIV", "EXPIRED"}
