from __future__ import annotations

import asyncio

import pytest

from gatum_rest_py import AuthenticationError


async def test_async_flow(aclient, api):
    assert await aclient.me() == {"echo": "/me"}
    result = await aclient.send_sms([str(380500000001 + 2 * i) for i in range(120)], sender_id="S", text="T")
    assert len(result.ids) == 120
    assert api.paths().count("/v1/send") == 2


async def test_async_concurrent_calls_login_once(aclient, api):
    await asyncio.gather(*(aclient.groups() for _ in range(10)))
    assert api.paths().count("/v1/access-token") == 1


async def test_async_relogin(aclient, api):
    await aclient.me()
    api.tokens.clear()
    assert await aclient.stat() == {"echo": "/stat"}
    assert api.paths().count("/v1/access-token") == 2


async def test_async_token_only_401(api):
    import httpx

    from gatum_rest_py import AsyncGatumClient

    from .conftest import BASE

    async with httpx.AsyncClient(transport=httpx.MockTransport(api)) as http:
        client = AsyncGatumClient("wrong", base_url=BASE, http_client=http)
        with pytest.raises(AuthenticationError):
            await client.me()
    assert len(api.calls) == 1
