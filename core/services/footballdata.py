
import requests

from django.conf import settings


class FootballDataError(Exception):
    pass


def football_request(endpoint, params=None):
    """
    Make an authenticated request to Footballdata.io.
    """

    api_key = settings.FOOTBALLDATA_API_KEY
    base_url = settings.FOOTBALLDATA_BASE_URL.rstrip("/")

    if not api_key:
        raise FootballDataError(
            "Football data API key is not configured."
        )

    url = f"{base_url}/{endpoint.lstrip('/')}"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params or {},
            timeout=30,
        )

        try:
            data = response.json()
        except ValueError:
            data = {}

        if not response.ok:
            error_data = data.get("error", {})
            message = error_data.get(
                "message",
                "Football data API request failed."
            )

            raise FootballDataError(
                f"API error ({response.status_code}): {message}"
            )

        if data.get("success") is False:
            error_data = data.get("error", {})
            raise FootballDataError(
                error_data.get("message", "API request failed.")
            )

        return data

    except requests.RequestException as exc:
        raise FootballDataError(
            f"Could not connect to Footballdata.io: {exc}"
        ) from exc


def get_today_fixtures():
    return football_request("fixtures/today")


def get_upcoming_fixtures():
    return football_request("fixtures/upcoming")


def get_live_fixtures():
    return football_request("fixtures/live")


def get_recent_results():
    return football_request("fixtures/results")


def search_teams(query):
    return football_request(
        "teams",
        params={"search": query}
    )


def search_matches(query):
    return football_request(
        "search",
        params={"q": query}
    )


def get_account_usage():
    return football_request("account/usage")


def get_match_statistics(match_id):
    return football_request(
        f"matches/{match_id}/stats"
    )


def get_head_to_head(team_id, opponent_id):
    return football_request(
        f"teams/{team_id}/h2h/{opponent_id}"
    )
