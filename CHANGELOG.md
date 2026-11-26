# Changelog

## 2.0.0 - unreleased

### Added
- `GatumClient` (sync) and `AsyncGatumClient` (asyncio) on httpx, with the same methods.
- Automatic token management: login on the first call, renewal when `expires_at` is reached, one retry after 401.
- `send()` / `send_sms()` split sends into batches of 100 SMS and return `SendResult` (`ids`, `failed`, `ok`).
- `Message` packages, so one request can carry different texts.
- New endpoints: `stat()`, `replacement()`, `product_price()`, `account_price()`, `country_price()`, `country_by_continent()`.
- New options: `callback_url`, `campaign`, `shortener`, more SMS types for `/send`; `state`, `id_state`, `offset` for `/sms-full-data`.
- Typed exceptions: `BadRequestError`, `AuthenticationError`, `PermissionDeniedError`, `RateLimitError` (`retry_after`), `TransportError`.
- DLR helpers (`parse_dlr`, `process_dlr`, `DeliveryReport`) and integrations for FastAPI, Django and Flask.
- `from_env()` configuration, `py.typed`, tests and CI.

### Changed
- Default base URL is `https://restapi.sempico.solutions`. Base URLs with or without a trailing `/` or `/v1` work.
- Packaging moved from `setup.py` to `pyproject.toml`; Python 3.10+.
- Phone numbers are sent as strings, as the API specifies.

### Deprecated
- `GatumRESTAPI` (the 1.x class). It still works, warns, and will be removed in 3.0.

### Fixed
- `GatumRESTAPI` built `https://host//v1/...` URLs when `base_url` ended with `/` (as in the old README).
- `requirements.txt` was saved in UTF-16 and could not be read by pip (removed; dependencies are in `pyproject.toml`).

## 1.0.0 - 2023
- First release.
