from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from mmcore_schema import DeviceType
from pymmcore_plus import CMMCorePlus, core_io

from ._py_config_model import ConfigGroup, ConfigPreset

if TYPE_CHECKING:
    from collections.abc import Iterable

    from mmcore_schema.state import DeviceInfo, PropertyInfo


def get_config_groups(core: CMMCorePlus) -> Iterable[ConfigGroup]:
    """Get the model for configuration groups."""
    channel_group = core.getChannelGroup()
    for state_group in core_io.read_config_groups(core):
        group = ConfigGroup(
            name=state_group.name,
            is_channel_group=(state_group.name == channel_group),
        )
        for state_preset in state_group.presets.values():
            preset = ConfigPreset(name=state_preset.name)
            for s in state_preset.settings:
                info = core_io.read_property_info(core, s.device, s.property)
                # use the preset's value, not the current core value
                preset.settings.append(dataclasses.replace(info, value=s.value))
            group.presets[preset.name] = preset
        yield group


def get_loaded_devices(core: CMMCorePlus) -> tuple[DeviceInfo, ...]:
    """Get all loaded devices with full property metadata."""
    return core_io.read_devices(core)


def get_available_devices(
    core: CMMCorePlus, *, exclude: set[tuple[str, str]] = frozenset()
) -> Iterable[DeviceInfo]:
    """Get all available (unloaded) devices."""
    for library in core.getDeviceAdapterNames():
        dev_names = core.getAvailableDevices(library)
        types = core.getAvailableDeviceTypes(library)
        descriptions = core.getAvailableDeviceDescriptions(library)
        for dev_name, description, dev_type in zip(
            dev_names, descriptions, types, strict=False
        ):
            if (library, dev_name) not in exclude:
                from mmcore_schema.state import DeviceInfo

                yield DeviceInfo(
                    label="",
                    name=dev_name,
                    library=library,
                    description=description,
                    type=DeviceType(dev_type),
                )
