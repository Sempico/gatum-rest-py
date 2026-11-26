"""FastAPI service: send OTP codes and receive delivery reports.

    pip install "gatum-rest-py[fastapi]" uvicorn
    export GATUM_USERNAME=your_login GATUM_PASSWORD=your_password GATUM_DLR_API_KEY=your-key
    export PUBLIC_URL=https://example.com
    uvicorn examples.fastapi_app:app
"""

import os
import secrets

from fastapi import Depends, FastAPI, HTTPException

from gatum_rest_py import APIError, AsyncGatumClient, DeliveryReport
from gatum_rest_py.integrations.fastapi import dlr_router, gatum_lifespan, get_gatum

PUBLIC_URL = os.environ.get("PUBLIC_URL", "https://example.com")
STATES: dict[int, str] = {}  # use a database in a real service


async def on_dlr(reports: list[DeliveryReport]) -> None:
    for report in reports:
        STATES[report.id_state] = report.state


app = FastAPI(title="OTP service", lifespan=gatum_lifespan())
app.include_router(dlr_router(on_dlr, api_key=os.environ.get("GATUM_DLR_API_KEY")))


@app.post("/otp/{phone}")
async def send_otp(phone: str, gatum: AsyncGatumClient = Depends(get_gatum)):
    code = f"{secrets.randbelow(10**6):06d}"
    try:
        result = await gatum.send_sms(
            phone, sender_id="Verify", text=f"Your code: {code}", lifetime=300,
            callback_url=f"{PUBLIC_URL}/gatum/dlr",
        )
    except APIError as exc:
        raise HTTPException(502, exc.message) from exc
    if not result.ok:
        raise HTTPException(422, result.failed[phone])
    return {"id_state": result.ids[phone]}


@app.get("/sms/{id_state}")
async def sms_state(id_state: int):
    return {"id_state": id_state, "state": STATES.get(id_state, "ENROUTE")}
