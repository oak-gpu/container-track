from .base import BaseTracker


class MSCTracker(BaseTracker):
    def track(self, container_id: str) -> dict:
        return {
            "status": "NOT SUPPORTED: MSC has no public API — track manually at msc.com",
            "location": "",
        }
