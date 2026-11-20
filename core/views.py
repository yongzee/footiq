from concurrent.futures import ThreadPoolExecutor, as_completed
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from .services.footballdata import (
    get_today_fixtures,
    get_upcoming_fixtures,
    get_live_fixtures,
    get_recent_results,
    FootballDataError,
)
from .services.managebetcodes import (
    view_bet_slip,
    ManageBetCodesError,
)

CHARS = "qwertyuiopasdfghjklzxcvbnm1234567890"


def home(request):
    return render(request, "core/home.html")


def _slip_has_draw(slip):
    """Return True if any selection in the betslip is a draw pick."""
    if not slip:
        return False

    selections = (
        slip.get("selections")
        if isinstance(slip, dict)
        else getattr(slip, "selections", [])
    )

    for item in selections or []:
        sel = str(
            item.get("selection")
            if isinstance(item, dict)
            else getattr(item, "selection", "")
        ).strip().lower()

        mkt = str(
            item.get("market")
            if isinstance(item, dict)
            else getattr(item, "market", "")
        ).strip().lower()

        if (
            "draw" in sel
            or sel == "x"
            or sel.endswith(" - x")
            or ("draw" in mkt and sel in {"x", "draw", "yes"})
        ):
            return True

    return False


def _attach_slip_metadata(slip, code=None):
    """Ensure code and has_draw flag are present on dict or object slips."""
    if not slip:
        return None

    has_draw = _slip_has_draw(slip)

    if isinstance(slip, dict):
        if code and not slip.get("code"):
            slip["code"] = code
        slip["has_draw"] = has_draw
    else:
        if code and not getattr(slip, "code", None):
            setattr(slip, "code", code)
        setattr(slip, "has_draw", has_draw)

    return slip


def _fetch_single_variant(variant, bookmaker):
    """Helper for parallel execution; ignores invalid/missing codes."""
    try:
        slip = view_bet_slip(variant, bookmaker)
        if slip:
            return _attach_slip_metadata(slip, code=variant)
    except ManageBetCodesError:
        return None
    return None


def _load_fixtures(fixture_type="today"):
    endpoints = {
        "today": get_today_fixtures,
        "upcoming": get_upcoming_fixtures,
        "live": get_live_fixtures,
        "results": get_recent_results,
    }
    selected = fixture_type if fixture_type in endpoints else "today"
    try:
        response = endpoints[selected]()
        if isinstance(response, list):
            matches = response
        elif isinstance(response, dict):
            data = response.get("data")
            if isinstance(data, dict):
                matches = data.get("matches", [])
            elif isinstance(data, list):
                matches = data
            else:
                matches = response.get("matches", [])
        else:
            matches = []
        return matches, selected, None
    except FootballDataError as exc:
        return [], selected, str(exc)


@require_http_methods(["GET", "POST"])
def check_bet_code(request):
    result = None
    batch_results = []
    error = None

    fixture_type = (
        request.POST.get("fixture_type")
        or request.GET.get("fixture_type", "today")
    )
    fixtures, selected_fixture_type, fixtures_error = _load_fixtures(fixture_type)

    if request.method == "POST":
        code = request.POST.get("code", "").strip().lower()
        bookmaker = request.POST.get("bookmaker", "").strip().lower()
        scan_mode = request.POST.get("scan_mode") == "on"

        if not code:
            error = "Please enter a booking code."

        elif bookmaker not in ["sportybet", "bet9ja"]:
            error = "Please select a supported bookmaker."

        elif scan_mode:
            variants = [f"{code}{c}" for c in CHARS]

            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {
                    executor.submit(_fetch_single_variant, variant, bookmaker): variant
                    for variant in variants
                }
                for future in as_completed(futures):
                    slip = future.result()
                    if slip:
                        batch_results.append(slip)

            if not batch_results:
                error = f"No valid betslips found when iterating '{code}'."

        else:
            try:
                raw_result = view_bet_slip(code, bookmaker)
                result = _attach_slip_metadata(raw_result, code=code)
            except ManageBetCodesError as exc:
                error = str(exc)

    return render(request, "core/check_bet_code.html", {
        "result": result,
        "batch_results": batch_results,
        "error": error,
        "fixtures": fixtures,
        "selected_fixture_type": selected_fixture_type,
        "fixtures_error": fixtures_error,
    })


def fixtures_centre(request):
    selected = request.GET.get("type", "today")

    endpoints = {
        "today": get_today_fixtures,
        "upcoming": get_upcoming_fixtures,
        "live": get_live_fixtures,
        "results": get_recent_results,
    }

    if selected not in endpoints:
        selected = "today"

    matches = []
    error = None
    meta = {}

    try:
        response = endpoints[selected]()
        if isinstance(response, dict):
            data = response.get("data") or {}
            matches = data.get("matches", []) if isinstance(data, dict) else []
            meta = response.get("meta") or {}

    except FootballDataError as exc:
        error = str(exc)

    return render(request, "core/fixtures.html", {
        "matches": matches,
        "selected": selected,
        "error": error,
        "meta": meta,
    })