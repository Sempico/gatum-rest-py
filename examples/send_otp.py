"""Send an OTP and print the result.

    export GATUM_USERNAME=your_login GATUM_PASSWORD=your_password
    python examples/send_otp.py 380501234567
"""

import secrets
import sys

from gatum_rest_py import APIError, GatumClient


def main(phone: str) -> None:
    code = f"{secrets.randbelow(10**6):06d}"
    with GatumClient.from_env() as client:
        try:
            result = client.send_sms(phone, sender_id="Verify", text=f"Your code: {code}", lifetime=300)
        except APIError as exc:
            sys.exit(f"Not sent: {exc}")
    if result.ok:
        print(f"Sent {code} to {phone}, id_state: {result.ids[phone]}")
    else:
        print(f"Rejected: {result.failed[phone]}")


if __name__ == "__main__":
    main(sys.argv[1])
