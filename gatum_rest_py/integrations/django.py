"""Django integration.

``settings.py``::

    GATUM = {
        "USERNAME": env("GATUM_USERNAME"),
        "PASSWORD": env("GATUM_PASSWORD"),
        # "ACCESS_TOKEN": "...",           # instead of username/password
        # "BASE_URL": "https://restapi.sempico.solutions",
        "DLR_API_KEY": env("GATUM_DLR_API_KEY", default=""),
    }

``urls.py``::

    from gatum_rest_py.integrations.django import dlr_view

    urlpatterns = [path("gatum/dlr/", dlr_view())]

Anywhere (for example in ``receivers.py`` of your app)::

    from django.dispatch import receiver
    from gatum_rest_py.integrations.django import dlr_received, get_client

    @receiver(dlr_received)
    def on_dlr(sender, reports, **kwargs):
        for r in reports:
            Message.objects.filter(id_state=r.id_state).update(state=r.state)

    get_client().send_sms("380501234567", sender_id="Verify", text="Code: 4242")
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from typing import Any

try:
    from django.conf import settings
    from django.core.signals import setting_changed
    from django.dispatch import Signal
    from django.http import HttpRequest, HttpResponse, JsonResponse
    from django.views.decorators.csrf import csrf_exempt
    from django.views.decorators.http import require_POST
except ImportError as exc:  # pragma: no cover
    raise ImportError('Django is not installed: pip install "gatum-rest-py[django]"') from exc

from ..client import GatumClient
from ..dlr import API_KEY_HEADER, DLRHandler, InvalidDLRRequest, process_dlr
from ..models import DeliveryReport

__all__ = ["dlr_received", "dlr_view", "get_client"]

#: Sent with ``reports=list[DeliveryReport]`` for every DLR request that
#: :func:`dlr_view` gets without its own handler.
dlr_received = Signal()

_client: GatumClient | None = None
_client_lock = threading.Lock()


def _config() -> dict[str, Any]:
    return dict(getattr(settings, "GATUM", {}))


def get_client() -> GatumClient:
    """One shared, thread-safe :class:`GatumClient` built from ``settings.GATUM``."""
    global _client
    with _client_lock:
        if _client is None:
            config = _config()
            kwargs = {
                key: config[key.upper()]
                for key in ("access_token", "username", "password", "base_url", "timeout")
                if config.get(key.upper())
            }
            _client = GatumClient(**kwargs)
        return _client


def _reset_client(*, setting: str, **kwargs: Any) -> None:
    global _client
    if setting == "GATUM" and _client is not None:
        _client.close()
        _client = None


setting_changed.connect(_reset_client)


def _send_signal(reports: list[DeliveryReport]) -> None:
    dlr_received.send(sender=dlr_view, reports=reports)


def dlr_view(
    handler: DLRHandler | None = None, *, api_key: str | None = None
) -> Callable[[HttpRequest], HttpResponse]:
    """A CSRF-exempt, POST-only view that receives DLR.

    Without ``handler`` every request sends the :data:`dlr_received` signal.
    ``api_key`` defaults to ``settings.GATUM["DLR_API_KEY"]``.
    """
    callback = handler or _send_signal

    @csrf_exempt
    @require_POST
    def view(request: HttpRequest) -> HttpResponse:
        expected = api_key if api_key is not None else _config().get("DLR_API_KEY")
        try:
            body = json.loads(request.body or b"null")
        except ValueError:
            return JsonResponse({"error": "Body is not JSON"}, status=400)
        try:
            ids = process_dlr(
                body,
                callback,
                api_key=request.headers.get(API_KEY_HEADER),
                expected_api_key=expected,
            )
        except InvalidDLRRequest as exc:
            return JsonResponse({"error": str(exc)}, status=exc.status_code)
        return JsonResponse(ids, safe=False)

    return view
