from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Result:
    ok: bool
    error: Optional[str] = None


class Backend(ABC):
    @abstractmethod
    def check_connection(self) -> Result:
        """Return Result(ok=True) if the device is reachable."""

    @abstractmethod
    def upload(self, file_path: str, filename: str) -> Result:
        """Upload a file to the device. filename is the destination name shown on the device."""
