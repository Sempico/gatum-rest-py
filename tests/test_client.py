from __future__ import annotations

from datetime import date, datetime, time

import httpx
import pytest

from gatum_rest_py import (
    AuthenticationError,
    BadRequestError,
    GatumClient,
    GatumError,
    Message,
    RateLimitError,
    TransportError,
)
from gatum_rest_py._base import normalize_base_url, plan_send

from .conftest import BASE, err


@pytest.mark.parametrize(
    "url", ["https://h", "https://h/", "https://h/v1", "https://h/v1/", " https://h "]
)
def test_base_url_normalized(url):
    assert normalize_base_url(url) == "https://h/v1"


def test_login_on_first_call_and_token_header(client, api):
    assert client.me() == {"echo": "/me"}
    assert api.paths() == ["/v1/authorize", "/v1/access-token", "/v1/me"]
    assert api.calls[-1].headers["X-Access-Token"] == "tok-2"
    assert api.calls[-1].method == "GET"
    assert client.token.expires_at == datetime(2099, 1, 1)


def test_wrong_password(api):
    http = httpx.Client(transport=httpx.MockTransport(api))
    c = GatumClient(username="u", password="bad", base_url=BASE, http_client=http)
    with pytest.raises(BadRequestError) as exc:
        c.me()
    assert exc.value.status_code == 400
    assert "Incorrect username or password" in exc.value.message


def test_relogin_on_401_once(client, api):
    client.me()
    api.tokens.clear()  # token destroyed on the server
    assert client.groups() == {"echo": "/group"}
    assert api.paths()[-3:] == ["/v1/authorize", "/v1/access-token", "/v1/group"]


def test_no_relogin_without_credentials(api):
    http = httpx.Client(transport=httpx.MockTransport(api))
    c = GatumClient("bad-token", base_url=BASE, http_client=http)
    with pytest.raises(AuthenticationError):
        c.me()
    assert len(api.calls) == 1


def test_token_only(api):
    http = httpx.Client(transport=httpx.MockTransport(api))
    assert GatumClient("tok-1", base_url=BASE, http_client=http).me() == {"echo": "/me"}


def test_no_auth_at_all():
    with pytest.raises(GatumError, match="No access token"):
        GatumClient(base_url=BASE).me()


def test_register_needs_no_token(client, api):
    client.register("l", "p", "n", "1", "e@x.io", company_name="ACME")
    assert api.paths() == ["/v1/register"]
    assert api.body() == {"login": "l", "password": "p", "name": "n", "phone": "1", "email": "e@x.io",
                          "company_name": "ACME"}


def test_rate_limit(client, api):
    api.overrides["/me"] = lambda r: err(429, "Too Many Requests", {"Retry-After": "42"})
    with pytest.raises(RateLimitError) as exc:
        client.me()
    assert exc.value.retry_after == 42


def test_non_json_answer(client, api):
    api.overrides["/me"] = lambda r: httpx.Response(502, text="<html>Bad gateway</html>")
    with pytest.raises(TransportError):
        client.me()


def test_network_error(client, api):
    def boom(request):
        raise httpx.ConnectError("down")

    api.overrides["/me"] = boom
    with pytest.raises(TransportError):
        client.me()


def test_send_sms_result_split(client, api):
    result = client.send_sms(
        ["380501111111", 380502222220], sender_id="Verify", text="Code",
        begin_date=date(2026, 1, 2), begin_time=time(10, 30), callback_url="https://me/dlr",
    )
    assert result.ids == {"380501111111": [380501111111]}
    assert result.failed == {"380502222220": "phone_in_black_list"}
    assert not result.ok
    assert api.body() == [{
        "number": ["380501111111", "380502222220"], "senderID": "Verify", "text": "Code", "type": "sms",
        "beginDate": "2026-01-02", "beginTime": "10:30:00", "callback_url": "https://me/dlr",
        "delivery": True,
    }]


def test_send_is_split_by_100(client, api):
    numbers = [str(380500000001 + i * 2) for i in range(250)]
    result = client.send_sms(numbers, sender_id="S", text="T")
    sends = [i for i, p in enumerate(api.paths()) if p == "/v1/send"]
    assert [len(api.body(i)[0]["number"]) for i in sends] == [100, 100, 50]
    assert len(result.ids) == 250


def test_plan_send_packs_packages():
    plans = plan_send([Message(["1"] * 70, "A", "x"), Message(["2"] * 70, "B", "y")])
    assert [[len(p["number"]) for p in body] for body in plans] == [[70, 30], [40]]
    assert plan_send([Message([], "A", "x")]) == []


def test_partial_result_on_failure(client, api):
    count = {"n": 0}

    def second_fails(request):
        count["n"] += 1
        if count["n"] == 2:
            return err(400, "No SMS was sent")
        from .conftest import ok
        return ok({"1": [{"id_state": 7}]})

    api.overrides["/send"] = second_fails
    with pytest.raises(BadRequestError) as exc:
        client.send_sms([str(i) for i in range(150)], sender_id="S", text="T")
    assert exc.value.partial_result.ids == {"1": [7]}


def test_payloads(client, api):
    client.sms_full_data(mcc=255, phone=[380501], time_period=(datetime(2026, 1, 1), datetime(2026, 1, 2)),
                         state=["DELIVERD"], limit=10)
    assert api.body() == {"MCC": 255, "phone": ["380501"],
                          "time_period": "2026-01-01 00:00:00 - 2026-01-02 00:00:00",
                          "state": ["DELIVERD"], "limit": 10}
    client.create_group("VIP", time_birth=time(9, 0), text_birth="Hi #first_name#", on_birth=True)
    assert api.body() == {"name_group": "VIP", "time_birth": "09:00", "text_birth": "Hi #first_name#",
                          "on_birth": True}
    client.delete_groups(5)
    assert api.body() == {"id_group": [5]}
    client.group_add_numbers(5, [380501, {"number": 380502, "name": "Ann", "date_birth": date(1990, 5, 1)}])
    assert api.body() == {"id_group": 5, "numbers": [
        {"number": "380501"}, {"number": "380502", "name": "Ann", "date_birth": "1990-05-01"}]}
    client.send_bulk("Shop", "Sale", 5, id_group_excluded=[6], time_start=time(10), time_stop="17:00")
    assert api.body() == {"senderID": "Shop", "text": "Sale", "id_group": [5], "id_group_excluded": [6],
                          "timeStart": "10:00:00", "timeStop": "17:00"}
    client.blacklist_add([1, "2"])
    assert api.body() == {"numbers": ["1", "2"]}
    client.replacement("380501", "S", "T")
    assert api.body() == [{"number": ["380501"], "senderID": "S", "text": "T"}]
    client.product_price(iso="IT", mcc=222, mnc=1)
    assert api.body() == {"ISO": "IT", "MCC": "222", "MNC": "1"}
    client.country_by_continent()
    assert api.body() == {}
    with pytest.raises(ValueError):
        client.account_price(mnc=1)


def test_logout(client, api):
    client.me()
    assert client.logout() == ["Logged Out Successfully"]
    assert client.token is None


def test_from_env(monkeypatch):
    monkeypatch.setenv("GATUM_ACCESS_TOKEN", "abc")
    monkeypatch.setenv("GATUM_BASE_URL", "https://x.io/")
    monkeypatch.setenv("GATUM_TIMEOUT", "5")
    c = GatumClient.from_env()
    assert c.token.token == "abc" and c.base_url == "https://x.io/v1"
    assert c._http.timeout.connect == 5
