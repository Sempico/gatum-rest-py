"""Synchronous client."""

from __future__ import annotations

import threading
from collections.abc import Iterable
from typing import Any

import httpx

from ._base import (
    DEFAULT_BASE_URL,
    DEFAULT_TIMEOUT,
    USER_AGENT,
    Endpoints,
    Number,
    env_kwargs,
    normalize_base_url,
    parse_response,
    plan_send,
)
from .exceptions import APIError, AuthenticationError, GatumError, TransportError
from .models import AccessToken, Message, SendResult

__all__ = ["GatumClient"]


class GatumClient(Endpoints[Any]):
    """Synchronous client for the Gatum REST API.

    Give it either a ready ``access_token``, or ``username`` and
    ``password``. With credentials the client gets a token on the first
    request, and gets a new one when the token expires or the API answers
    401 (once per request).

    Example::

        with GatumClient(username="login", password="secret") as client:
            result = client.send_sms(["380501234567"], sender_id="Verify", text="Code: 4242")
            print(result.ids, result.failed)

    Every method returns the ``data`` of the answer and raises an
    :class:`~gatum_rest_py.exceptions.APIError` subclass when the API
    answers ``"status": false``.
    """

    def __init__(
        self,
        access_token: str | None = None,
        *,
        username: str | None = None,
        password: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.base_url = normalize_base_url(base_url)
        self._username = username
        self._password = password
        self._token: AccessToken | None = (
            AccessToken(access_token, None) if access_token else None
        )
        self._lock = threading.Lock()
        self._own_http = http_client is None
        self._http = http_client or httpx.Client(timeout=timeout)
        self._http.headers.setdefault("User-Agent", USER_AGENT)

    @classmethod
    def from_env(cls, prefix: str = "GATUM_", **overrides: Any) -> GatumClient:
        """Build a client from ``GATUM_ACCESS_TOKEN`` / ``GATUM_USERNAME`` / ``GATUM_PASSWORD``
        / ``GATUM_BASE_URL`` / ``GATUM_TIMEOUT``. Keyword arguments win over the environment."""
        return cls(**{**env_kwargs(prefix), **overrides})

    # --- lifecycle --------------------------------------------------------

    def close(self) -> None:
        if self._own_http:
            self._http.close()

    def __enter__(self) -> GatumClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # --- auth -------------------------------------------------------------

    @property
    def token(self) -> AccessToken | None:
        """The current token (``None`` before the first login)."""
        return self._token

    def login(self, username: str | None = None, password: str | None = None) -> AccessToken:
        """Run ``/authorize`` + ``/access-token`` and keep the token in the client."""
        username = username or self._username
        password = password or self._password
        if not username or not password:
            raise GatumError("login() needs a username and a password")
        self._username, self._password = username, password
        code = self._request(
            "POST", "/authorize", {"username": username, "password": password}, token=None
        )
        data = self._request(
            "POST", "/access-token", {"authorization_code": code["authorization_code"]}, token=None
        )
        self._token = AccessToken.from_data(data)
        return self._token

    def logout(self) -> Any:
        """Destroy the token on the server (``GET /logout``)."""
        data = self._call("GET", "/logout", relogin=False)
        self._token = None
        return data

    @property
    def _can_login(self) -> bool:
        return bool(self._username and self._password)

    def _ensure_token(self) -> str:
        with self._lock:
            if self._token is None or (self._can_login and self._token.is_expired()):
                if not self._can_login:
                    raise GatumError(
                        "No access token: pass access_token=... or username/password to the client"
                    )
                self.login()
            assert self._token is not None
            return self._token.token

    # --- transport --------------------------------------------------------

    def _request(self, method: str, path: str, payload: Any, *, token: str | None) -> Any:
        headers = {"X-Access-Token": token} if token else {}
        try:
            response = self._http.request(
                method,
                self.base_url + path,
                json=payload if method != "GET" else None,
                headers=headers,
            )
        except httpx.HTTPError as exc:
            raise TransportError(f"{method} {path}: {exc}") from exc
        return parse_response(response.status_code, response.headers, response.content)

    def _call(
        self, method: str, path: str, payload: Any = None, *, auth: bool = True, relogin: bool = True
    ) -> Any:
        if not auth:
            return self._request(method, path, payload, token=None)
        token = self._ensure_token()
        try:
            return self._request(method, path, payload, token=token)
        except AuthenticationError:
            if not (relogin and self._can_login):
                raise
            with self._lock:
                if self._token is None or self._token.token == token:
                    self.login()
                token = self._token.token  # type: ignore[union-attr]
            return self._request(method, path, payload, token=token)

    # --- sending ----------------------------------------------------------

    def send(self, messages: Iterable[Message] | Message) -> SendResult:
        """Send one or more :class:`Message` packages.

        The API takes up to 100 SMS per request; bigger sends are split
        into several requests made one after another, as the API requires.
        If a request fails, the raised :class:`APIError` has the result of
        the requests already made in ``exc.partial_result``.
        """
        if isinstance(messages, Message):
            messages = [messages]
        result = SendResult()
        for body in plan_send(messages):
            try:
                result.merge(self._call("POST", "/send", body) or {})
            except APIError as exc:
                exc.partial_result = result  # type: ignore[attr-defined]
                raise
        return result

    def send_sms(
        self, numbers: Iterable[Number] | Number, sender_id: str, text: str, **options: Any
    ) -> SendResult:
        """Send one text to one or many numbers.

        ``options`` are the other fields of :class:`Message`: ``type``,
        ``begin_date``, ``begin_time``, ``lifetime``, ``callback_url``,
        ``delivery``, ``campaign``, ``shortener``.
        """
        return self.send(Message(numbers, sender_id, text, **options))
