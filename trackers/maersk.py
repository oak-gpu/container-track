import time
import requests
import config
from .base import BaseTracker

_TOKEN_URL = "https://api.maersk.com/customer-identity/oauth/v2/token"
_EVENTS_URL = "https://api.maersk.com/track-and-trace-private/v2/events"

_cached_token: str = ""
_token_expiry: float = 0.0


def _get_token() -> str:
    global _cached_token, _token_expiry
    if _cached_token and time.time() < _token_expiry - 30:
        return _cached_token
    resp = requests.post(
        _TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": config.MAERSK_CLIENT_ID,
            "client_secret": config.MAERSK_CLIENT_SECRET,
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    _cached_token = data["access_token"]
    _token_expiry = time.time() + data.get("expires_in", 3600)
    return _cached_token


class MaerskTracker(BaseTracker):
    def track(self, container_id: str) -> dict:
        if not config.MAERSK_CLIENT_ID or not config.MAERSK_CLIENT_SECRET:
            return {"status": "ERROR: Maersk API credentials not configured", "location": ""}
        try:
            token = _get_token()
            resp = requests.get(
                _EVENTS_URL,
                params={"equipmentReference": container_id},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Consumer-Key": config.MAERSK_CLIENT_ID,
                    "Accept": "application/json",
                },
                timeout=20,
            )
            resp.raise_for_status()
            return _parse(resp.json())
        except requests.HTTPError as e:
            return {"status": f"ERROR: HTTP {e.response.status_code} — {e.response.text[:120]}", "location": ""}
        except Exception as e:
            return {"status": f"ERROR: {e}", "location": ""}


def _parse(data) -> dict:
    # DCSA v2.2 response: list of event objects, newest first
    if isinstance(data, dict):
        events = data.get("events") or []
    elif isinstance(data, list):
        events = data
    else:
        events = []

    # prefer ACT (actual) events over EST/PLN
    actual = [e for e in events if e.get("eventClassifierCode") == "ACT"]
    events = actual or events

    if not events:
        return {"status": "No events found", "location": ""}

    latest = events[0]
    status = (
        latest.get("description")
        or latest.get("eventDescription")
        or latest.get("equipmentEventTypeCode")
        or latest.get("transportEventTypeCode")
        or latest.get("shipmentEventTypeCode")
        or "Unknown"
    )
    loc = (
        _dig(latest, "location", "locationName")
        or _dig(latest, "location", "UNLocationCode")
        or latest.get("portName")
        or ""
    )
    return {"status": status, "location": loc}


def _dig(d, *keys):
    for k in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d
