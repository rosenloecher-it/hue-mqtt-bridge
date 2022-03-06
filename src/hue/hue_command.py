from __future__ import annotations
from enum import Enum
from typing import Optional

import attr


class HueCommandType(Enum):
    SWITCH = "switch"
    DIM = "dim"
    # COLOR = "color"

    def __str__(self):
        return self.value

    def __repr__(self) -> str:
        return '{}.{}'.format(self.__class__.__name__, self.name)


class SwitchType(Enum):
    ON = "on"
    OFF = "off"
    TOGGLE = "toggle"

    def __str__(self):
        return self.value

    def __repr__(self) -> str:
        return '{}.{}'.format(self.__class__.__name__, self.name)


@attr.frozen
class HueCommand:

    type: HueCommandType
    switch: SwitchType
    dim: float
    # color: str

    @classmethod
    def create_switch(cls, switch: SwitchType):
        return HueCommand(type=HueCommandType.SWITCH, switch=switch, dim=None)

    @classmethod
    def create_dim(cls, dim: int):
        if dim == 0:
            return HueCommand(type=HueCommandType.SWITCH, switch=SwitchType.OFF, dim=None, color=None)
        elif 1 <= dim <= 100:
            return HueCommand(type=HueCommandType.DIM, switch=None, dim=dim)
        else:
            raise ValueError(f"Invalid dim value ({dim})")

    # @class method
    # def create_color(cls, color: str):
    #     return HueCommand(type=HueCommandType.COLOR, switch=None, dim=None, color=color)

    @classmethod
    def parse(cls, text: Optional[str]) -> HueCommand:
        orig_text = text

        if isinstance(text, bytes):
            text = text.decode("utf-8")

        if text:
            text = text.upper().strip()

        command = None

        if text:
            if text in ["ON", "TRUE"]:
                command = cls.create_switch(SwitchType.ON)
            elif text in ["OFF", "FALSE"]:
                command = cls.create_switch(SwitchType.OFF)
            elif text == "TOGGLE":
                command = cls.create_switch(SwitchType.TOGGLE)
            else:
                try:
                    value = int(text)
                    if value == 0:
                        return cls.create_switch(SwitchType.OFF)
                    elif 1 <= value <= 100:
                        return cls.create_dim(value)
                except ValueError:
                    pass

        if command is None:
            raise ValueError("cannot parse to command ({})!".format(orig_text))

        return command
