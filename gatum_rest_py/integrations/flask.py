"""Flask integration.

Usage::

    from flask import Flask
    from gatum_rest_py.integrations.flask import Gatum

    app = Flask(__name__)
    app.config.update(GATUM_USERNAME="login", GATUM_PASSWORD="secret", GATUM_DLR_API_KEY="key")
    gatum = Gatum(app)

    @gatum.on_dlr
    def handle(reports):
        for r in reports:
            print(r.id_state, r.state)

    @app.post("/otp")
    def otp():
        result = gatum.client.send_sms("380501234567", sender_id="Verify", text="Code: 4242")
        return {"ids": result.ids, "failed": result.failed}
"""

from __future__ import annotations

from typing import Any

try:
    from flask import Blueprint, Flask, current_app, jsonify, request
except ImportError as exc:  # pragma: no cover
    raise ImportError('Flask is not installed: pip install "gatum-rest-py[flask]"') from exc

from ..client import GatumClient
from ..dlr import API_KEY_HEADER, DLRHandler, InvalidDLRRequest, process_dlr

__all__ = ["Gatum", "dlr_blueprint"]

_EXT = "gatum"


def dlr_blueprint(
    handler: DLRHandler,
    *,
    url: str = "/gatum/dlr",
    api_key: str | None = None,
    name: str = "gatum_dlr",
) -> Blueprint:
    """A blueprint with a ``POST`` endpoint that receives DLR.

    ``handler`` gets ``list[DeliveryReport]`` and may return the reports to
    confirm (``None`` confirms all). If ``api_key`` is ``None``, the
    ``GATUM_DLR_API_KEY`` config value is used, if set.
    """
    bp = Blueprint(name, __name__)

    @bp.post(url)
    def receive_dlr():
        expected = api_key if api_key is not None else current_app.config.get("GATUM_DLR_API_KEY")
        try:
            ids = process_dlr(
                request.get_json(silent=True),
                handler,
                api_key=request.headers.get(API_KEY_HEADER),
                expected_api_key=expected,
            )
        except InvalidDLRRequest as exc:
            return jsonify(error=str(exc)), exc.status_code
        return jsonify(ids)

    return bp


class Gatum:
    """Flask extension: one :class:`GatumClient` per app, configured from ``app.config``.

    Config keys: ``GATUM_ACCESS_TOKEN``, ``GATUM_USERNAME``, ``GATUM_PASSWORD``,
    ``GATUM_BASE_URL``, ``GATUM_TIMEOUT``, ``GATUM_DLR_URL`` (default
    ``/gatum/dlr``), ``GATUM_DLR_API_KEY``.
    """

    def __init__(self, app: Flask | None = None) -> None:
        self._app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        kwargs: dict[str, Any] = {}
        for key in ("access_token", "username", "password", "base_url", "timeout"):
            value = app.config.get(f"GATUM_{key.upper()}")
            if value:
                kwargs[key] = value
        app.extensions[_EXT] = GatumClient(**kwargs)

    @property
    def client(self) -> GatumClient:
        """The client of the current app."""
        app = current_app if self._app is None else self._app
        return app.extensions[_EXT]

    def on_dlr(self, handler: DLRHandler) -> DLRHandler:
        """Decorator: register ``handler`` as the DLR webhook of the app."""
        if self._app is None:
            raise RuntimeError("Use dlr_blueprint() with the app factory pattern")
        url = self._app.config.get("GATUM_DLR_URL", "/gatum/dlr")
        self._app.register_blueprint(dlr_blueprint(handler, url=url))
        return handler
