"""Flask app: send SMS and receive delivery reports.

    pip install "gatum-rest-py[flask]"
    export GATUM_USERNAME=your_login GATUM_PASSWORD=your_password
    flask --app examples.flask_app run
"""

import os

from flask import Flask, abort, request

from gatum_rest_py import APIError
from gatum_rest_py.integrations.flask import Gatum

app = Flask(__name__)
app.config.update(
    GATUM_USERNAME=os.environ.get("GATUM_USERNAME"),
    GATUM_PASSWORD=os.environ.get("GATUM_PASSWORD"),
    GATUM_DLR_API_KEY=os.environ.get("GATUM_DLR_API_KEY"),
)
gatum = Gatum(app)


@gatum.on_dlr
def handle_dlr(reports):
    for r in reports:
        app.logger.info("SMS %s to %s: %s", r.id_state, r.phone, r.state)


@app.post("/notify")
def notify():
    data = request.get_json(force=True)
    try:
        result = gatum.client.send_sms(data["phones"], sender_id="Shop", text=data["text"])
    except APIError as exc:
        abort(502, exc.message)
    return {"ids": result.ids, "failed": result.failed}
