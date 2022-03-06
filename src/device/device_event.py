from enum import Enum
from typing import Optional

import attr


class DeviceStatus(Enum):
    ERROR = "error"
    OFF = "off"
    OFFLINE = "offline"
    ON = "on"


@attr.define
class DeviceEvent:

    status: Optional[DeviceStatus] = None
    id: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None

    brightness: Optional[float] = None

    # later: color: Optional[str] = None  # missing color transformations
