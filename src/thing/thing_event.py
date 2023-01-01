from enum import Enum
from typing import Optional, Dict

import attr

from src.utils.time_utils import TimeUtils


class ThingStatus(Enum):
    ERROR = "error"
    OFF = "off"
    OFFLINE = "offline"
    ON = "on"


@attr.define
class ThingEvent:

    status: Optional[ThingStatus] = None
    id: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None

    brightness: Optional[float] = None

    # later: color: Optional[str] = None  # missing color transformations

    def to_data(self) -> Dict[str, any]:
        data = {
            "name": self.name
        }

        if not self.status:
            data["status"] = "error"
        else:
            data["status"] = self.status.value

        if self.brightness is not None:
            data["brightness"] = int(round(self.brightness))

        data["timestamp"] = TimeUtils.now(no_ms=True)

        return data
