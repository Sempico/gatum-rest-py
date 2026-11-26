"""Asynchronous client (asyncio), for FastAPI, aiohttp, Django async views and so on."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Iterable
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

__all__ = ["AsyncGatumClient"]


class AsyncGatumClient(Endpoints[Awaitable[Any]]):
    """Asynchronous twin of :class:`~gatum_rest_py.GatumClient`.

    Same methods and arguments; every method is awaited::

        async with AsyncGatumClient(username="login", password="secret") as client:
            result = await client.send_sms("380501234567", sender_id="Verify", text="Code: 4242")
    """

    def __init__(
        self,
        access_token: str | None = None,
        *,
        username: str | None = None,
        password: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float | httpx.Timeout = DEFAULT_TIMEOUT,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = normalize_base_url(base_url)
        self._username = username
        self._password = password
        self._token: AccessToken | None = (
            AccessToken(access_token, None) if access_token else None
        )
        self._lock = asyncio.Lock()
        self._own_http = http_client is None
        self._http = http_client or httpx.AsyncClient(timeout=timeout)
        self._http.headers.setdefault("User-Agent", USER_AGENT)

    @classmethod
    def from_env(cls, prefix: str = "GATUM_", **overrides: Any) -> AsyncGatumClient:
        """Build a client from ``GATUM_ACCESS_TOKEN`` / ``GATUM_USERNAME`` / ``GATUM_PASSWORD``
        / ``GATUM_BASE_URL`` / ``GATUM_TIMEOUT``. Keyword arguments win over the environment."""
        return cls(**{**env_kwargs(prefix), **overrides})

    async def aclose(self) -> None:
        if self._own_http:
            await self._http.aclose()

    async def __aenter__(self) -> AsyncGatumClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    @property
    def token(self) -> AccessToken | None:
        return self._token

    async def login(self, username: str | None = None, password: str | None = None) -> AccessToken:
        username = username or self._username
        password = password or self._password
        if not username or not password:
            raise GatumError("login() needs a username and a password")
        self._username, self._password = username, password
        code = await self._request(
            "POST", "/authorize", {"username": username, "password": password}, token=None
        )
        data = await self._request(
            "POST", "/access-token", {"authorization_code": code["authorization_code"]}, token=None
        )
        self._token = AccessToken.from_data(data)
        return self._token

    async def logout(self) -> Any:
        data = await self._call("GET", "/logout", relogin=False)
        self._token = None
        return data

    @property
    def _can_login(self) -> bool:
        return bool(self._username and self._password)

    async def _ensure_token(self) -> str:
        async with self._lock:
            if self._token is None or (self._can_login and self._token.is_expired()):
                if not self._can_login:
                    raise GatumError(
                        "No access token: pass access_token=... or username/password to the client"
                    )
                await self.login()
            assert self._token is not None
            return self._token.token

    async def _request(self, method: str, path: str, payload: Any, *, token: str | None) -> Any:
        headers = {"X-Access-Token": token} if token else {}
        try:
            response = await self._http.request(
                method,
                self.base_url + path,
                json=payload if method != "GET" else None,
                headers=headers,
            )
        except httpx.HTTPError as exc:
            raise TransportError(f"{method} {path}: {exc}") from exc
        return parse_response(response.status_code, response.headers, response.content)

    async def _call(  # type: ignore[override]
        self, method: str, path: str, payload: Any = None, *, auth: bool = True, relogin: bool = True
    ) -> Any:
        if not auth:
            return await self._request(method, path, payload, token=None)
        token = await self._ensure_token()
        try:
            return await self._request(method, path, payload, token=token)
        except AuthenticationError:
            if not (relogin and self._can_login):
                raise
            async with self._lock:
                if self._token is None or self._token.token == token:
                    await self.login()
                token = self._token.token  # type: ignore[union-attr]
            return await self._request(method, path, payload, token=token)

    async def send(self, messages: Iterable[Message] | Message) -> SendResult:
        """See :meth:`GatumClient.send`. Batches are sent one after another, never in parallel."""
        if isinstance(messages, Message):
            messages = [messages]
        result = SendResult()
        for body in plan_send(messages):
            try:
                result.merge(await self._call("POST", "/send", body) or {})
            except APIError as exc:
                exc.partial_result = result  # type: ignore[attr-defined]
                raise
        return result

    async def send_sms(
        self, numbers: Iterable[Number] | Number, sender_id: str, text: str, **options: Any
    ) -> SendResult:
        return await self.send(Message(numbers, sender_id, text, **options))
