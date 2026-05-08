from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Result:
    ok: bool
    error: Optional[str] = None
    uuid: Optional[str] = None  # reMarkable UUID assigned by the backend on upload


class Backend(ABC):
    @abstractmethod
    def check_connection(self) -> Result:
        """Return Result(ok=True) if the device is reachable."""

    @abstractmethod
    def upload(self, file_path: str, filename: str, title: str = None, calibre_uuid: str = None) -> Result:
        """Upload a file to the device. Returns Result.uuid with the reMarkable UUID assigned."""
