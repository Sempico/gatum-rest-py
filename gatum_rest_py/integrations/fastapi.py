"""FastAPI / Starlette integration.

Usage::

    from fastapi import Depends, FastAPI
    from gatum_rest_py import AsyncGatumClient, DeliveryReport
    from gatum_rest_py.integrations.fastapi import dlr_router, gatum_lifespan, get_gatum

    async def on_dlr(reports: list[DeliveryReport]) -> None:
        for r in reports:
            print(r.id_state, r.phone, r.state)

    app = FastAPI(lifespan=gatum_lifespan())           # one client for the whole app
    app.include_router(dlr_router(on_dlr, api_key="secret"))

    @app.post("/otp")
    async def otp(phone: str, gatum: AsyncGatumClient = Depends(get_gatum)):
        result = await gatum.send_sms(phone, sender_id="Verify", text="Code: 4242")
        return {"ids": result.ids, "failed": result.failed}
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

try:
    from fastapi import APIRouter, Request
    from fastapi.responses import JSONResponse
    from starlette.concurrency import run_in_threadpool
except ImportError as exc:  # pragma: no cover
    raise ImportError('FastAPI is not installed: pip install "gatum-rest-py[fastapi]"') from exc

from ..async_client import AsyncGatumClient
from ..dlr import API_KEY_HEADER, DLRHandler, InvalidDLRRequest, aprocess_dlr

__all__ = ["dlr_router", "gatum_lifespan", "get_gatum"]

_STATE_KEY = "gatum"


def dlr_router(
    handler: DLRHandler,
    *,
    path: str = "/gatum/dlr",
    api_key: str | None = None,
    **router_kwargs: Any,
) -> APIRouter:
    """An ``APIRouter`` with a ``POST`` endpoint that receives DLR.

    ``handler`` gets ``list[DeliveryReport]``; it may be ``async def`` or a
    plain function (then it runs in the thread pool). It may return the
    reports to confirm; ``None`` confirms all. ``api_key`` is checked
    against the ``API_KEY`` header.
    """
    router = APIRouter(**router_kwargs)
    # A plain function must not block the event loop: run it in the thread pool.
    call = handler if inspect.iscoroutinefunction(handler) else functools.partial(run_in_threadpool, handler)

    @router.post(path, include_in_schema=False)
    async def receive_dlr(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except ValueError:
            return JSONResponse({"error": "Body is not JSON"}, status_code=400)
        try:
            ids = await aprocess_dlr(
                body,
                call,
                api_key=request.headers.get(API_KEY_HEADER),
                expected_api_key=api_key,
            )
        except InvalidDLRRequest as exc:
            return JSONResponse({"error": str(exc)}, status_code=exc.status_code)
        return JSONResponse(ids)

    return router


def gatum_lifespan(
    client_factory: Callable[[], AsyncGatumClient] = AsyncGatumClient.from_env,
):
    """A lifespan that opens one :class:`AsyncGatumClient` for the app and closes it on shutdown.

    By default the client is configured from ``GATUM_*`` environment variables.
    """

    @asynccontextmanager
    async def lifespan(app: Any) -> AsyncIterator[None]:
        client = client_factory()
        setattr(app.state, _STATE_KEY, client)
        try:
            yield
        finally:
            await client.aclose()

    return lifespan


def get_gatum(request: Request) -> AsyncGatumClient:
    """Dependency: the client opened by :func:`gatum_lifespan`."""
    client = getattr(request.app.state, _STATE_KEY, None)
    if client is None:
        raise RuntimeError("Gatum client is not set up: FastAPI(lifespan=gatum_lifespan())")
    return client
