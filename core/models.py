from dataclasses import dataclass
from typing import Any


@dataclass
class Response:
    success: bool
    message: str
    source: str = "system"
    response_type: str = "reply"
    data: Any = None
