from __future__ import annotations

import json

import pytest

from .test_dlr import BODY


class TestFastAPI:
    @pytest.fixture
    def app(self):
        pytest.importorskip("fastapi")
        from fastapi import FastAPI

        from gatum_rest_py.integrations.fastapi import dlr_router

        self.seen = []

        async def on_dlr(reports):
            self.seen.extend(reports)

        app = FastAPI()
        app.include_router(dlr_router(on_dlr, api_key="key"))
        return app

    def test_ok(self, app):
        from fastapi.testclient import TestClient

        r = TestClient(app).post("/gatum/dlr", json=BODY, headers={"API_KEY": "key"})
        assert r.status_code == 200 and r.json() == [598933232, 598933233]
        assert len(self.seen) == 2

    def test_wrong_key(self, app):
        from fastapi.testclient import TestClient

        r = TestClient(app).post("/gatum/dlr", json=BODY, headers={"API_KEY": "nope"})
        assert r.status_code == 403 and not self.seen

    def test_sync_handler_and_lifespan(self, monkeypatch):
        pytest.importorskip("fastapi")
        from fastapi import Depends, FastAPI
        from fastapi.testclient import TestClient

        from gatum_rest_py import AsyncGatumClient
        from gatum_rest_py.integrations.fastapi import dlr_router, gatum_lifespan, get_gatum

        monkeypatch.setenv("GATUM_ACCESS_TOKEN", "t")
        app = FastAPI(lifespan=gatum_lifespan())
        app.include_router(dlr_router(lambda rs: rs[:1]))

        @app.get("/who")
        async def who(gatum: AsyncGatumClient = Depends(get_gatum)):
            return {"token": gatum.token.token}

        with TestClient(app) as tc:
            assert tc.post("/gatum/dlr", json=BODY).json() == [598933232]
            assert tc.get("/who").json() == {"token": "t"}


class TestFlask:
    def test_extension(self):
        pytest.importorskip("flask")
        from flask import Flask

        from gatum_rest_py.integrations.flask import Gatum

        app = Flask(__name__)
        app.config.update(GATUM_ACCESS_TOKEN="t", GATUM_DLR_API_KEY="key")
        gatum = Gatum(app)
        seen = []
        gatum.on_dlr(seen.extend)

        tc = app.test_client()
        r = tc.post("/gatum/dlr", json=BODY, headers={"API_KEY": "key"})
        assert r.status_code == 200 and r.get_json() == [598933232, 598933233]
        assert tc.post("/gatum/dlr", json=BODY).status_code == 403
        assert tc.post("/gatum/dlr", data="nope", headers={"API_KEY": "key"}).status_code == 400
        with app.app_context():
            assert gatum.client.token.token == "t"
        assert len(seen) == 2


class TestDjango:
    @pytest.fixture(autouse=True)
    def django_setup(self):
        pytest.importorskip("django")
        import django
        from django.conf import settings

        if not settings.configured:
            settings.configure(
                DEBUG=True, ROOT_URLCONF=__name__, ALLOWED_HOSTS=["*"],
                GATUM={"ACCESS_TOKEN": "t", "DLR_API_KEY": "key"},
            )
            django.setup()

    def test_signal_view(self):
        from django.test import RequestFactory

        from gatum_rest_py.integrations.django import dlr_received, dlr_view, get_client

        seen = []

        def receiver(sender, reports, **kwargs):
            seen.extend(reports)

        dlr_received.connect(receiver)
        try:
            view = dlr_view()
            rf = RequestFactory()
            ok = view(rf.post("/d", data=json.dumps(BODY), content_type="application/json",
                              headers={"API_KEY": "key"}))
            assert ok.status_code == 200 and json.loads(ok.content) == [598933232, 598933233]
            bad = view(rf.post("/d", data=json.dumps(BODY), content_type="application/json"))
            assert bad.status_code == 403
            assert view(rf.get("/d")).status_code == 405
        finally:
            dlr_received.disconnect(receiver)
        assert len(seen) == 2
        assert get_client().token.token == "t"

    def test_custom_handler(self):
        from django.test import RequestFactory

        from gatum_rest_py.integrations.django import dlr_view

        view = dlr_view(lambda rs: [], api_key="")
        r = view(RequestFactory().post("/d", data=json.dumps(BODY), content_type="application/json"))
        assert json.loads(r.content) == []


urlpatterns: list = []
