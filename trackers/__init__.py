from .maersk import MaerskTracker
from .hapag_lloyd import HapagLloydTracker
from .cma_cgm import CMACGMTracker
from .msc import MSCTracker

_REGISTRY = {
    "maersk":       MaerskTracker,
    "hapag-lloyd":  HapagLloydTracker,
    "hapag lloyd":  HapagLloydTracker,
    "hapag":        HapagLloydTracker,
    "hl":           HapagLloydTracker,
    "cma cgm":      CMACGMTracker,
    "cma-cgm":      CMACGMTracker,
    "cmacgm":       CMACGMTracker,
    "cma":          CMACGMTracker,
    "msc":          MSCTracker,
}


def get_tracker(carrier_name: str):
    # Strip suffixes like "/ BARSAN" or "/ AGENT NAME" from carrier cell values
    key = carrier_name.split("/")[0].strip().lower()
    cls = _REGISTRY.get(key)
    if cls:
        return cls()
    return _UnknownTracker(carrier_name)


class _UnknownTracker:
    def __init__(self, name):
        self._name = name

    def track(self, container_id: str) -> dict:
        return {"status": f"NOT SUPPORTED: unknown carrier '{self._name}'", "location": ""}
