"""MyShipTracking AIS integration — vessel name → MMSI lookup + position/ETA fetch."""
import re
import requests
import config

_SEARCH_URL = "https://api.myshiptracking.com/api/v2/vessel/search"
_VESSEL_URL = "https://api.myshiptracking.com/api/v2/vessel"

_mmsi_cache: dict[str, int] = {}
_status_cache: dict[int, dict] = {}


def _headers() -> dict:
    return {"Authorization": f"Bearer {config.MYSHIPTRACKING_API_KEY}"}


def _extract_vessel_name(raw: str) -> str:
    """Strip voyage code from vessel/voyage name strings.

    Handles both formats found in Excel:
      'ADRASTOS 0HWJZW1MA'        → 'ADRASTOS'
      'RAPHAELA ( 0HWK1W1MA)'     → 'RAPHAELA'
      'IRENES POWER ( 1BM2GS1MA)' → 'IRENES POWER'
    """
    s = raw.strip()
    s = re.sub(r"\s*\(.*\)\s*$", "", s).strip()
    tokens = s.split()
    if len(tokens) > 1 and re.match(r"^\d[A-Z0-9]+$", tokens[-1]):
        s = " ".join(tokens[:-1])
    return s


def is_us_port(code: str) -> bool:
    """Check if a UN/LOCODE or port name refers to a US port."""
    if not code:
        return False
    code = code.strip().upper()
    return code.startswith("US") and len(code) >= 4


def _port_name(port_field) -> str:
    """Extract a readable port name from either a string or dict."""
    if not port_field:
        return ""
    if isinstance(port_field, dict):
        return port_field.get("name") or port_field.get("unlocode") or ""
    return str(port_field)


def _port_locode(port_field) -> str:
    """Extract UN/LOCODE from either a string or dict."""
    if not port_field:
        return ""
    if isinstance(port_field, dict):
        return port_field.get("unlocode") or port_field.get("name") or ""
    return str(port_field)


def resolve_mmsi(vessel_raw: str, cached_mmsi) -> tuple[int | None, str]:
    """Return (mmsi, error_message). Uses cached_mmsi if already set."""
    if cached_mmsi:
        try:
            return int(cached_mmsi), ""
        except (ValueError, TypeError):
            pass

    name = _extract_vessel_name(vessel_raw)
    if name in _mmsi_cache:
        return _mmsi_cache[name], ""

    if not config.MYSHIPTRACKING_API_KEY:
        return None, "MyShipTracking API key not configured"

    try:
        resp = requests.get(
            _SEARCH_URL,
            params={"name": name},
            headers=_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json().get("data") or []
        if not data:
            return None, f"No vessel found for '{name}'"

        exact = [v for v in data if v.get("vessel_name", "").upper() == name.upper()]
        vessel = exact[0] if exact else data[0]
        mmsi = int(vessel["mmsi"])
        _mmsi_cache[name] = mmsi
        return mmsi, ""
    except requests.HTTPError as e:
        return None, f"Search HTTP {e.response.status_code}: {e.response.text[:100]}"
    except Exception as e:
        return None, f"Search error: {e}"


def get_vessel_status(mmsi: int) -> dict:
    """Return vessel status dict including current port and next port info."""
    if mmsi in _status_cache:
        return _status_cache[mmsi]

    if not config.MYSHIPTRACKING_API_KEY:
        return {"error": "MyShipTracking API key not configured"}

    try:
        resp = requests.get(
            _VESSEL_URL,
            params={"mmsi": mmsi, "response": "extended"},
            headers=_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        d = resp.json().get("data") or {}
        cur_port = d.get("current_port") or {}
        arrived_at = ""
        if isinstance(cur_port, dict):
            arrived_at = cur_port.get("arrived_at") or cur_port.get("arrival_time") or ""

        result = {
            "nav_status":       d.get("nav_status") or "",
            "destination":      d.get("destination") or "",
            "eta":              d.get("eta") or "",
            "current_port":     cur_port,
            "arrived_at":       arrived_at,
            "next_port":        d.get("next_port") or "",
            "next_port_eta":    d.get("next_port_eta_utc") or d.get("next_port_eta_local") or "",
            "speed":            d.get("speed") or "",
            "lat":              d.get("lat") or "",
            "lng":              d.get("lng") or "",
            "error":            "",
        }
        _status_cache[mmsi] = result
        return result
    except requests.HTTPError as e:
        return {"error": f"Vessel HTTP {e.response.status_code}: {e.response.text[:100]}"}
    except Exception as e:
        return {"error": f"Vessel error: {e}"}


def clear_run_cache():
    """Call between tracking runs so stale positions aren't reused."""
    _mmsi_cache.clear()
    _status_cache.clear()
