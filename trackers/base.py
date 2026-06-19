from abc import ABC, abstractmethod


class BaseTracker(ABC):
    @abstractmethod
    def track(self, container_id: str) -> dict:
        """
        Returns dict with keys:
          status   (str)  — latest event description
          location (str)  — latest port/place, empty string if unknown
        """
