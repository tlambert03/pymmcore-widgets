from __future__ import annotations

from dataclasses import dataclass, field

from mmcore_schema.state import PropertyInfo


@dataclass
class ConfigPreset:
    """A named preset -- settings are PropertyInfo with full metadata."""

    name: str = ""
    settings: list[PropertyInfo] = field(default_factory=list)


@dataclass
class ConfigGroup:
    """A group of configuration presets."""

    name: str = ""
    presets: dict[str, ConfigPreset] = field(default_factory=dict)
    is_channel_group: bool = False

    @property
    def is_system_group(self) -> bool:
        return self.name.lower() == "system"
