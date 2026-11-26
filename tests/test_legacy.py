"""The deprecated 1.x class must keep working."""

from __future__ import annotations

import pytest


def test_legacy_import_and_urls(monkeypatch):
    import gatum_rest_py

    with pytest.warns(DeprecationWarning):
        client = gatum_rest_py.GatumRESTAPI(base_url="https://restapi.gatum.io/")

    sent = []

    class Resp:
        status_code = 200

        def json(self):
            return {"status": True, "data": {}}

    import requests

    monkeypatch.setattr(requests, "post", lambda url, **kw: sent.append(url) or Resp())
    monkeypatch.setattr(requests, "get", lambda url, **kw: sent.append(url) or Resp())
    client.send_sms("tok", ["1"], "S", "T")
    client.account_info("tok")
    assert sent == ["https://restapi.gatum.io/v1/send", "https://restapi.gatum.io/v1/me"]
