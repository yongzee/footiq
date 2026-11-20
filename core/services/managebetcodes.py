
import os
import requests

from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv(
    "MANAGEBETCODES_BASE_URL",
    "https://api.managebetcodes.app/v1"
)

API_KEY = os.getenv("MANAGEBETCODES_API_KEY")


class ManageBetCodesError(Exception):
    pass


def view_bet_slip(code, bookmaker):
    """
    Retrieve a submitted booking code as structured JSON.
    """

    if not API_KEY:
        raise ManageBetCodesError("API key is not configured.")

    url = f"{BASE_URL}/view"

    headers = {
        "X-API-Key": API_KEY,
        "Accept": "application/json",
    }

    params = {
        "code": code,
        "bookmaker": bookmaker,
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30,
        )

        try:
            data = response.json()
        except ValueError:
            data = {}

        if response.status_code != 200:
            message = data.get(
                "message",
                data.get("error", "API request failed.")
            )
            raise ManageBetCodesError(
                f"API error ({response.status_code}): {message}"
            )

        return data

    except requests.RequestException as exc:
        raise ManageBetCodesError(
            f"Could not connect to Manage Bet Codes: {exc}"
        ) from exc
