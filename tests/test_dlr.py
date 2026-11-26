from __future__ import annotations

import pytest

from gatum_rest_py import DeliveryReport, confirm, parse_dlr
from gatum_rest_py.dlr import InvalidDLRRequest, aprocess_dlr, check_api_key, process_dlr

BODY = [
    {"id_state": 598933232, "originator": "SMS", "phone": "380957225759", "type_sms": "sms",
     "text_sms": "Your OTP is 42432", "num_parts": 1, "part_no": 1, "state": "DELIVRD",
     "time": "2023-07-24 12:03:48", "price": 0.03},
    {"id_state": 598933233, "originator": "SMS", "phone": "380957225758", "type_sms": "sms",
     "text_sms": "Your OTP is 42432", "num_parts": 1, "part_no": 1, "state": "UNDELIV",
     "time": "2023-07-24 12:03:48", "error": 12},
]


def test_parse():
    reports = parse_dlr(BODY)
    assert reports[0].delivered and reports[0].final and reports[0].price == 0.03
    assert not reports[1].delivered and reports[1].error == 12
    assert reports[1].raw == BODY[1]
    assert parse_dlr(BODY[0])[0].id_state == 598933232


@pytest.mark.parametrize("body", [None, "x", [{"phone": "1"}]])
def test_parse_invalid(body):
    with pytest.raises(InvalidDLRRequest):
        parse_dlr(body)


def test_confirm():
    assert confirm([DeliveryReport(1, "p", "DELIVRD"), 2, "3"]) == [1, 2, 3]


def test_api_key():
    check_api_key(None, None)
    check_api_key("k", "k")
    with pytest.raises(InvalidDLRRequest) as exc:
        check_api_key("bad", "k")
    assert exc.value.status_code == 403
    with pytest.raises(InvalidDLRRequest):
        check_api_key(None, "k")


def test_process_confirms_all_by_default():
    seen = []
    assert process_dlr(BODY, seen.extend) == [598933232, 598933233]
    assert len(seen) == 2


def test_process_confirms_returned_only():
    assert process_dlr(BODY, lambda rs: [r for r in rs if r.delivered]) == [598933232]


def test_process_rejects_async_handler():
    async def h(rs):
        return None

    with pytest.raises(TypeError):
        process_dlr(BODY, h)


async def test_aprocess_async_handler():
    async def h(rs):
        return [rs[1]]

    assert await aprocess_dlr(BODY, h) == [598933233]
