from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, TypeAlias

from mmcore_schema import DeviceType, PropertyType

from pymmcore_widgets._icons import StandardIcon

if TYPE_CHECKING:
    from collections.abc import Hashable

AffineTuple: TypeAlias = tuple[float, float, float, float, float, float]


@dataclass
class Device:
    """A device in the system."""

    label: str = ""
    name: str = ""
    library: str = ""
    description: str = ""
    type: DeviceType = DeviceType.Unknown
    properties: tuple[DevicePropertySetting, ...] = ()

    @property
    def is_loaded(self) -> bool:
        return bool(self.label)

    @property
    def iconify_key(self) -> str | None:
        return StandardIcon.for_device_type(self.type)

    def key(self) -> Hashable:
        return (self.library, self.name)


@dataclass
class DevicePropertySetting:
    """A property setting enriched with metadata for UI display."""

    device_label: str = ""
    property_name: str = ""
    value: str = ""

    property_type: PropertyType = PropertyType.Undef
    is_read_only: bool = False
    is_pre_init: bool = False
    allowed_values: tuple[str, ...] = ()
    limits: tuple[float, float] | None = None
    sequence_max_length: int = 0
    device_type: DeviceType = DeviceType.Unknown

    # back-reference (not included in equality)
    parent: ConfigPreset | None = field(default=None, repr=False, compare=False)

    def key(self) -> tuple[str, str]:
        return (self.device_label, self.property_name)

    def as_tuple(self) -> tuple[str, str, str]:
        return (self.device_label, self.property_name, self.value)

    @property
    def iconify_key(self) -> StandardIcon | None:
        if self.is_read_only:
            return StandardIcon.READ_ONLY
        if self.is_pre_init:
            return StandardIcon.PRE_INIT
        return None

    @property
    def is_advanced(self) -> bool:
        if self.device_type == DeviceType.State and self.property_name == "State":
            return True
        return False

    def display_name(self) -> str:
        return f"{self.device_label}-{self.property_name}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DevicePropertySetting):
            return NotImplemented
        return (
            self.device_label == other.device_label
            and self.property_name == other.property_name
            and self.value == other.value
            and self.is_read_only == other.is_read_only
            and self.is_pre_init == other.is_pre_init
            and self.allowed_values == other.allowed_values
            and self.limits == other.limits
            and self.property_type == other.property_type
            and self.sequence_max_length == other.sequence_max_length
        )


@dataclass
class ConfigPreset:
    """A named preset within a config group."""

    name: str = ""
    settings: list[DevicePropertySetting] = field(default_factory=list)

    # back-reference (not included in equality)
    parent: ConfigGroup | None = field(default=None, repr=False, compare=False)

    @property
    def is_system_startup(self) -> bool:
        return (
            self.name.lower() == "startup"
            and self.parent is not None
            and self.parent.is_system_group
        )

    @property
    def is_system_shutdown(self) -> bool:
        return (
            self.name.lower() == "shutdown"
            and self.parent is not None
            and self.parent.is_system_group
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ConfigPreset):
            return NotImplemented
        return self.name == other.name and self.settings == other.settings


@dataclass
class ConfigGroup:
    """A group of configuration presets."""

    name: str = ""
    presets: dict[str, ConfigPreset] = field(default_factory=dict)
    is_channel_group: bool = False

    @property
    def is_system_group(self) -> bool:
        return self.name.lower() == "system"


@dataclass
class PixelSizePreset(ConfigPreset):
    """A pixel size preset with calibration data."""

    pixel_size_um: float = 0.0
    affine: AffineTuple = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0)
    dxdz: float = 0.0
    dydz: float = 0.0
    optimalz_um: float = 0.0


@dataclass
class PixelSizeConfigs(ConfigGroup):
    """Config group specialized for pixel size presets."""

    name: str = "PixelSizeGroup"
    presets: dict[str, PixelSizePreset] = field(default_factory=dict)  # type: ignore[assignment]
    is_channel_group: bool = False
