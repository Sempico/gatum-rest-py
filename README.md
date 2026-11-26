<p align="center">
  <a href="https://sempico.solutions">
    <img src="https://sempico.solutions/wp-content/uploads/2025/09/Logo.png" alt="Sempico Solutions" height="64">
  </a>
</p>

<h1 align="center">gatum-rest-py</h1>

<p align="center">
  The official Python SDK for the <a href="https://restapi.sempico.solutions/desc/">Sempico / Gatum REST API</a>:<br>
  SMS, OTP, HLR and MNP lookups, campaigns, groups, black list, prices and delivery reports.
</p>

<p align="center">
  <a href="https://pypi.org/project/gatum-rest-py/"><img src="https://img.shields.io/pypi/v/gatum-rest-py.svg" alt="PyPI"></a>
  <a href="https://pypi.org/project/gatum-rest-py/"><img src="https://img.shields.io/pypi/pyversions/gatum-rest-py.svg" alt="Python versions"></a>
  <a href="https://github.com/Sempico/gatum-rest-py/actions/workflows/ci.yml"><img src="https://github.com/Sempico/gatum-rest-py/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT license"></a>
</p>

---

* **Sync and async** clients (`GatumClient`, `AsyncGatumClient`) built on [httpx](https://www.python-httpx.org/), with the same methods.
* **Token management:** log in once with your login and password. The client gets a token, renews it when it expires and retries once after a `401`.
* **Big sends without counting:** `/send` takes up to 100 SMS per request; the client splits bigger sends into batches and sends them one after another.
* **Clear results and errors:** methods return the `data` of the answer. `SendResult` separates the accepted numbers from the failed ones, and errors are typed exceptions (`AuthenticationError`, `RateLimitError` with `retry_after`, ...).
* **Delivery reports (DLR)** out of the box for **FastAPI**, **Django** and **Flask**, with `API_KEY` check and confirmation.
* Fully typed (`py.typed`), Python 3.10+.

## Contents

- [Installation](#installation)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Sending SMS](#sending-sms)
- [All methods](#all-methods)
- [Errors and rate limits](#errors-and-rate-limits)
- [Delivery reports (DLR)](#delivery-reports-dlr)
- [Frameworks: FastAPI](#fastapi) · [Django](#django) · [Flask](#flask)
- [Migrating from 1.x](#migrating-from-1x)

## Installation

```bash
pip install gatum-rest-py

# with a framework integration
pip install "gatum-rest-py[fastapi]"   # or [django], [flask]
```

## Quick start

```python
from gatum_rest_py import GatumClient

with GatumClient(username="your_login", password="your_password") as client:
    print(client.me())  # {'login': ..., 'balance_units': 1000, 'currency': 'USD', ...}

    result = client.send_sms(["380501234567", "380671234567"], sender_id="Verify", text="Your code: 4242")
    print(result.ids)     # {'380501234567': [1855153903], ...}  - id_state of every SMS part
    print(result.failed)  # {'380671234567': 'phone_in_black_list'}
```

Async:

```python
import asyncio
from gatum_rest_py import AsyncGatumClient

async def main():
    async with AsyncGatumClient(username="your_login", password="your_password") as client:
        result = await client.send_sms("380501234567", sender_id="Verify", text="Your code: 4242")
        print(result.ok, result.ids)

asyncio.run(main())
```

## Configuration

```python
GatumClient(
    access_token=None,        # a ready token, or ...
    username=None,            # ... the login and
    password=None,            #     password of your web account (the token is managed for you)
    base_url="https://restapi.sempico.solutions",  # the URL of your vendor; with or without /v1
    timeout=30.0,
    http_client=None,         # your own httpx.Client (proxies, retries, mTLS, ...)
)
```

Keep credentials out of the code: `GatumClient.from_env()` reads
`GATUM_USERNAME`, `GATUM_PASSWORD`, `GATUM_ACCESS_TOKEN`, `GATUM_BASE_URL` and `GATUM_TIMEOUT`.

```python
client = GatumClient.from_env()
```

To manage the token yourself:

```python
token = client.login()          # AccessToken(token='...', expires_at=datetime(...))
client = GatumClient(token.token)
client.logout()                 # destroys the token on the server
```

> If your account has an IP white list, add the IPs of your servers to it, otherwise every request fails with `PermissionDeniedError: IP is not in WhiteList`.

## Sending SMS

```python
from datetime import date, time
from gatum_rest_py import Message

# one text, many numbers - any count, batches of 100 are made for you
client.send_sms(numbers, sender_id="Shop", text="Sale -20% today")

# all options
client.send_sms(
    ["380501234567"],
    sender_id="Verify",            # numeric 3-15 symbols, alphanumeric up to 11
    text="Your code: 4242",
    type="sms",                    # sms, flashsms, wappush, vcard, hlr, mnp
    begin_date=date(2026, 12, 1),  # scheduled sending (GMT+0); strings also work: "2026-12-01"
    begin_time=time(9, 30),        #                               "09:30" / "09:30:00"
    lifetime=3600,                 # seconds the system tries to deliver
    callback_url="https://example.com/gatum/dlr",  # DLR for this request
    delivery=True,                 # send DLR
    campaign="Black Friday",       # campaign name in the statistics
)

# different texts in one call
client.send([
    Message(["380501234567"], "Verify", "Code 1111"),
    Message(["380671234567", "380931234567"], "Shop", "Your order is ready"),
])

# HLR / MNP lookup
client.send_sms("380501234567", sender_id="HLR", text="__HLR__", type="hlr")
```

`send` / `send_sms` return a `SendResult`:

| Attribute | Meaning |
|---|---|
| `ids` | `{phone: [id_state, ...]}` of the created SMS (one id per part) |
| `failed` | `{phone: error_code}`, for example `phone_in_black_list`, `no_money`, `incorrect_originator` |
| `ok` | `True` when nothing failed |
| `raw` | the merged `data` of the answers |

Keep `id_state`: it links the SMS to its delivery reports and to `sms_full_data(id_state=[...])`.

## All methods

Every method returns the `data` of the answer. The arguments follow the
[API reference](https://restapi.sempico.solutions/desc/); in the async client every method is awaited.

| Area | Method | Endpoint |
|---|---|---|
| Auth | `login()`, `logout()` | `/authorize`, `/access-token`, `/logout` |
| Account | `me()` | `GET /me` |
| | `register(login, password, name, phone, email, company_name=, skype=)` | `/register` |
| SMS | `send_sms(numbers, sender_id, text, **options)`, `send(messages)` | `/send` |
| | `replacement(numbers, sender_id, text)` - check the replacement rules without sending | `/replacement` |
| Statistics | `sms_full_data(mcc=, mnc=, sender_id=, phone=, id_base=, time_period=, type_sms=, state=, id_state=, limit=, offset=)` | `/sms-full-data` |
| | `stat(groups_choose=, destination=, date_range=, type_sms=, id_name_delivery=)` | `/stat` |
| Groups | `groups(id_group=, limit=, offset=)`, `create_group(name, ...)`, `delete_groups(ids)` | `/group`, `/group-create`, `/group-delete` |
| Numbers in groups | `group_add_numbers(id_group, numbers)`, `group_search_numbers(...)`, `group_delete_numbers(...)` | `/group-number-*` |
| Campaigns | `send_bulk(sender_id, text, id_group, id_group_excluded=, phone=, date_start=, time_start=, time_stop=)` | `/send-bulk` |
| Black list | `blacklist_add(numbers)`, `blacklist_search(numbers)`, `blacklist_delete(numbers)` | `/black-list-*` |
| Prices | `product_price(iso=, mcc=, mnc=)`, `account_price(...)`, `country_price(iso=, mcc=)`, `country_by_continent()` | `/product-price`, ... |

<details>
<summary>Examples: groups, campaigns, black list, statistics, prices</summary>

```python
from datetime import date, datetime, time, timedelta

# groups
group = client.create_group("VIP", time_birth=time(10), originator_birth="Shop",
                            text_birth="Happy birthday, #first_name#!", on_birth=True)
id_group = group["group"]["list"][0]["id_group"]

client.group_add_numbers(id_group, [
    "380501234567",
    {"number": "380671234567", "name": "Olena", "date_birth": date(1992, 12, 31), "male": "f", "note_1": "gold"},
])
client.group_search_numbers(id_group, ["380501234567"])
client.groups(limit=100, offset=0)

# campaign to groups, sent gradually from 10:00 to 17:00
client.send_bulk("Shop", "Sale -20% today", id_group=[id_group], id_group_excluded=[42],
                 date_start=date(2026, 12, 1), time_start=time(10), time_stop=time(17))

# black list (up to 1000 numbers per request)
client.blacklist_add(["380501234567"])

# statistics (rate limit: 1 request per 15 minutes)
now = datetime.now()
client.sms_full_data(time_period=(now - timedelta(days=1), now), state=["DELIVERD"])
client.stat(groups_choose=["day"], date_range=(now - timedelta(days=7), now))

# prices
client.country_price(iso="UA")
client.account_price(mcc=255)
client.country_by_continent()
```

</details>

## Errors and rate limits

```python
from gatum_rest_py import APIError, AuthenticationError, RateLimitError, TransportError

try:
    client.me()
except RateLimitError as e:          # 429
    print("retry in", e.retry_after, "seconds")
except AuthenticationError:          # 401 - wrong/expired token and no credentials to renew it
    ...
except APIError as e:                # any other {"status": false}: e.status_code, e.errors, e.message
    print(e.status_code, e.message)
except TransportError:               # network error or not-JSON answer
    ...
```

| Exception | HTTP | When |
|---|---|---|
| `BadRequestError` | 400 | wrong data, e.g. `password: Incorrect username or password.`, `No SMS was sent` |
| `AuthenticationError` | 401 | the token is missing, wrong, expired or logged out |
| `PermissionDeniedError` | 403 | IP is not in the white list, REST API is not allowed for the account |
| `RateLimitError` | 429 | the rate limit was exceeded, see `retry_after` |
| `TransportError` | - | the API was not reached or the answer is not JSON |

All of them inherit from `GatumError`.

Rate limits of the API (per IP): `/register` - 2 per hour; `/me`, `/stat`, `/sms-full-data` - 1 per 15 minutes;
`/send` - 100 SMS per request, requests one after another. The client does not retry 429 for you,
because waiting 15 minutes inside a request is rarely what you want. Cache `me()` and use DLR instead of polling `sms_full_data()`.

If a batched send fails in the middle, the exception has the result of the batches already sent:

```python
try:
    client.send_sms(numbers, sender_id="Shop", text="...")
except APIError as e:
    done = e.partial_result   # SendResult of the batches sent before the error
```

## Delivery reports (DLR)

The API sends the state of every SMS part with a `POST` (a JSON array) to the `callback_url` of the send, or
to the URL set in the web account (**API → REST API → DLR sending to webhook**):

```json
[{"id_state": 598933232, "originator": "SMS", "phone": "380957225759", "type_sms": "sms",
  "text_sms": "Your OTP is 42432", "num_parts": 1, "part_no": 1, "state": "DELIVRD",
  "time": "2023-07-24 12:03:48", "price": 0.03}]
```

`state` is one of `DELIVRD`, `UNDELIV`, `EXPIRED`, `ENROUTE`. If a security key is set for the account, it comes in
the `API_KEY` header. Answer HTTP 200; in the confirmation mode, answer with the JSON array of the confirmed
`id_state`. A report is sent at most twice (the second time after about 30 seconds), so make the handler idempotent.

The integrations below do all of this. Your handler gets `list[DeliveryReport]` and may return the reports to
confirm; returning `None` confirms all of them.

`DeliveryReport` fields: `id_state`, `phone`, `state`, `originator`, `type_sms`, `text_sms`, `num_parts`, `part_no`,
`time`, `price`, `error`, `hlr`, `raw`, and the properties `delivered` and `final`.

> **The `API_KEY` header has an underscore.** nginx drops such headers by default: add
> `underscores_in_headers on;`. Gunicorn ≥ 22 drops them too: run it with `--header-map dangerous`, or check the
> key in nginx. Otherwise every DLR is rejected with 403.

Without a framework, or with any other one, use the core functions:

```python
from gatum_rest_py.dlr import process_dlr, InvalidDLRRequest

def on_reports(reports):
    for r in reports:
        save_state(r.id_state, r.state)

try:
    answer = process_dlr(json_body, on_reports, api_key=headers.get("API_KEY"), expected_api_key="secret")
    # respond 200 with JSON `answer`
except InvalidDLRRequest as e:
    ...  # respond e.status_code (400 or 403)
```

## Frameworks

### FastAPI

```python
from fastapi import Depends, FastAPI
from gatum_rest_py import AsyncGatumClient, DeliveryReport
from gatum_rest_py.integrations.fastapi import dlr_router, gatum_lifespan, get_gatum

async def on_dlr(reports: list[DeliveryReport]) -> None:
    for r in reports:
        await db.execute("UPDATE sms SET state = :s WHERE id_state = :id", {"s": r.state, "id": r.id_state})

# One client per app, opened and closed with the app, configured from GATUM_* env variables
app = FastAPI(lifespan=gatum_lifespan())
app.include_router(dlr_router(on_dlr, path="/gatum/dlr", api_key="your-dlr-key"))

@app.post("/otp")
async def send_otp(phone: str, gatum: AsyncGatumClient = Depends(get_gatum)):
    result = await gatum.send_sms(phone, sender_id="Verify", text="Your code: 4242",
                                  callback_url="https://example.com/gatum/dlr")
    return {"ids": result.ids, "failed": result.failed}
```

`dlr_router` accepts `async def` and plain functions (those run in the thread pool). To build the client
yourself: `gatum_lifespan(lambda: AsyncGatumClient(username=..., password=...))`.

### Django

`settings.py`:

```python
GATUM = {
    "USERNAME": os.environ["GATUM_USERNAME"],
    "PASSWORD": os.environ["GATUM_PASSWORD"],
    # "ACCESS_TOKEN": "...",                          # instead of username/password
    # "BASE_URL": "https://restapi.sempico.solutions",
    "DLR_API_KEY": os.environ.get("GATUM_DLR_API_KEY", ""),
}
```

`urls.py`:

```python
from django.urls import path
from gatum_rest_py.integrations.django import dlr_view

urlpatterns = [
    path("gatum/dlr/", dlr_view()),   # CSRF-exempt, POST only, checks API_KEY
]
```

Handle the reports with a signal (for example in `yourapp/receivers.py`, imported in `AppConfig.ready()`):

```python
from django.dispatch import receiver
from gatum_rest_py.integrations.django import dlr_received

@receiver(dlr_received)
def on_dlr(sender, reports, **kwargs):
    for r in reports:
        Sms.objects.filter(id_state=r.id_state).update(state=r.state)
```

or pass a handler directly: `dlr_view(my_handler)`. Send from views, tasks (Celery, RQ) or management commands:

```python
from gatum_rest_py.integrations.django import get_client

get_client().send_sms(user.phone, sender_id="Verify", text=f"Your code: {code}")
```

`get_client()` returns one shared thread-safe client built from `settings.GATUM`. For async views, create an
`AsyncGatumClient` with the same settings.

### Flask

```python
from flask import Flask
from gatum_rest_py.integrations.flask import Gatum

app = Flask(__name__)
app.config.update(
    GATUM_USERNAME="your_login",
    GATUM_PASSWORD="your_password",
    GATUM_DLR_API_KEY="your-dlr-key",   # optional
    GATUM_DLR_URL="/gatum/dlr",         # default
)
gatum = Gatum(app)

@gatum.on_dlr
def handle_dlr(reports):
    for r in reports:
        app.logger.info("SMS %s to %s: %s", r.id_state, r.phone, r.state)

@app.post("/otp")
def send_otp():
    result = gatum.client.send_sms("380501234567", sender_id="Verify", text="Your code: 4242")
    return {"ids": result.ids, "failed": result.failed}
```

With the app factory pattern: `gatum = Gatum()`, then `gatum.init_app(app)` and
`app.register_blueprint(dlr_blueprint(handle_dlr))` (from the same module).

More complete examples are in [`examples/`](examples).

## Migrating from 1.x

The 1.x class `GatumRESTAPI` still works in 2.x and shows a `DeprecationWarning`. It will be removed in 3.0.

| 1.x | 2.x |
|---|---|
| `client = GatumRESTAPI(base_url=...)` | `client = GatumClient(username=..., password=..., base_url=...)` |
| `client.access_token(username, password)` and passing `access_token=` to every call | not needed: the client manages the token (or `GatumClient(access_token)`) |
| `response.json()["data"]`, checking `status_code` | the method returns `data`, errors are exceptions |
| `account_info()` | `me()` |
| `register_customer(...)` | `register(...)` |
| `list_group()`, `delete_group()` | `groups()`, `delete_groups()` |
| `group_number_add/search/delete()` | `group_add_numbers/search_numbers/delete_numbers()` |
| `black_list_add/search/delete()` | `blacklist_add/search/delete()` |
| `send_sms(..., sms_type=...)` | `send_sms(..., type=...)`, returns `SendResult` |
| `sms_full_data(sender_id=...)` sent the deprecated `sender` field | sends `senderID` |
| — | new: `stat()`, `replacement()`, prices, `logout()`, async client, DLR integrations |

## Links

* API reference: <https://restapi.sempico.solutions/desc/> (OpenAPI: <https://restapi.sempico.solutions/openapi.json>)
* Sempico Solutions: <https://sempico.solutions> · support: support@sempico.solutions
* [Changelog](CHANGELOG.md) · [License: MIT](LICENSE)
