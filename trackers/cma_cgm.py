import requests
import config
from .base import BaseTracker

_EVENTS_URL = "https://api-portal.cma-cgm.com/tracking/v2/events"


class CMACGMTracker(BaseTracker):
    def track(self, container_id: str) -> dict:
        if not config.CMA_CGM_API_KEY:
            return {"status": "ERROR: CMA CGM API key not configured", "location": ""}
        try:
            resp = requests.get(
                _EVENTS_URL,
                params={"equipmentReference": container_id},
                headers={
                    "X-API-KEY": config.CMA_CGM_API_KEY,
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
    # DCSA v2.2 response: list of event objects or wrapped in {"events": [...]}
    if isinstance(data, dict):
        events = data.get("events") or []
    elif isinstance(data, list):
        events = data
    else:
        events = []

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
