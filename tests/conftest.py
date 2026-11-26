from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest

BASE = "https://api.test"


class FakeAPI:
    """Minimal in-memory imitation of the REST API."""

    def __init__(self) -> None:
        self.calls: list[httpx.Request] = []
        self.tokens = {"tok-1"}
        self.issued = 0
        self.overrides: dict[str, Callable[[httpx.Request], httpx.Response]] = {}

    def body(self, index: int = -1) -> Any:
        return json.loads(self.calls[index].content or b"null")

    def paths(self) -> list[str]:
        return [c.url.path for c in self.calls]

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        path = request.url.path.removeprefix("/v1")
        if path in self.overrides:
            return self.overrides[path](request)
        if path == "/authorize":
            data = json.loads(request.content)
            if data.get("password") != "secret":
                return err(400, {"password": ["Incorrect username or password."]})
            return ok({"authorization_code": "code", "expires_at": "2099-01-01 00:00:00"})
        if path == "/access-token":
            self.issued += 1
            token = f"tok-{self.issued + 1}"
            self.tokens.add(token)
            return ok({"access_token": token, "expires_at": "2099-01-01 00:00:00"})
        if path == "/register":
            return ok({"status": True, "info": "Account registered successfully"})
        if request.headers.get("X-Access-Token") not in self.tokens:
            return err(401, "Invalid Access token")
        if path == "/send":
            result = {}
            for package in json.loads(request.content):
                for n in package["number"]:
                    item = {"error": "phone_in_black_list"} if n.endswith("0") else {"id_state": int(n)}
                    result[n] = [item]
            return ok(result)
        if path == "/logout":
            self.tokens.discard(request.headers["X-Access-Token"])
            return ok(["Logged Out Successfully"])
        return ok({"echo": path})


def ok(data: Any) -> httpx.Response:
    return httpx.Response(200, json={"status": True, "data": data})


def err(code: int, errors: Any, headers: dict[str, str] | None = None) -> httpx.Response:
    return httpx.Response(code, json={"status": False, "error_code": code, "errors": errors}, headers=headers)


@pytest.fixture
def api() -> FakeAPI:
    return FakeAPI()


@pytest.fixture
def client(api: FakeAPI):
    from gatum_rest_py import GatumClient

    http = httpx.Client(transport=httpx.MockTransport(api))
    with GatumClient(username="user", password="secret", base_url=BASE, http_client=http) as c:
        yield c


@pytest.fixture
async def aclient(api: FakeAPI):
    from gatum_rest_py import AsyncGatumClient

    http = httpx.AsyncClient(transport=httpx.MockTransport(api))
    async with AsyncGatumClient(username="user", password="secret", base_url=BASE, http_client=http) as c:
        yield c
    await http.aclose()
