from __future__ import annotations

from typing import TYPE_CHECKING

from mmcore_schema import DeviceType
from pymmcore_plus import CMMCorePlus
from pymmcore_plus import core_io

from ._py_config_model import ConfigGroup, ConfigPreset, Device, DevicePropertySetting

if TYPE_CHECKING:
    from collections.abc import Container, Iterable

    from mmcore_schema import PropertySetting
    from mmcore_schema.state import ConfigPreset as StateConfigPreset


def get_config_groups(core: CMMCorePlus) -> Iterable[ConfigGroup]:
    """Get the model for configuration groups."""
    channel_group = core.getChannelGroup()
    for state_group in core_io.read_config_groups(core):
        group_model = ConfigGroup(
            name=state_group.name,
            is_channel_group=(state_group.name == channel_group),
        )
        for state_preset in state_group.presets.values():
            preset_model = _convert_preset(core, state_preset)
            preset_model.parent = group_model
            group_model.presets[preset_model.name] = preset_model
        yield group_model


def get_config_presets(core: CMMCorePlus, group: str) -> Iterable[ConfigPreset]:
    """Get all available configuration presets for a group."""
    state_group = core_io.read_config_group(core, group)
    for state_preset in state_group.presets.values():
        yield _convert_preset(core, state_preset)


def get_preset_settings(
    core: CMMCorePlus, group: str, preset: str
) -> Iterable[DevicePropertySetting]:
    """Get settings for a specific preset."""
    state_group = core_io.read_config_group(core, group)
    state_preset = state_group.presets[preset]
    for s in state_preset.settings:
        yield _convert_setting(core, s)


def get_property_info(
    core: CMMCorePlus, device_label: str, property_name: str
) -> dict:
    """Get information about a property of a device.

    Does *NOT* include the current value of the property.
    """
    prop = core_io.read_property_info(core, device_label, property_name)
    seq_max = 0
    if core.isPropertySequenceable(device_label, property_name):
        seq_max = core.getPropertySequenceMaxLength(device_label, property_name)
    return {
        "property_name": property_name,
        "property_type": prop.data_type,
        "is_read_only": prop.is_read_only,
        "is_pre_init": prop.is_pre_init,
        "allowed_values": prop.allowed_values,
        "sequence_max_length": seq_max,
        "limits": prop.limits,
    }


def get_loaded_devices(core: CMMCorePlus) -> Iterable[Device]:
    """Get the model for all loaded devices."""
    for state_dev in core_io.read_devices(core):
        dev = Device(
            label=state_dev.label,
            name=state_dev.name,
            description=state_dev.description,
            library=state_dev.library,
            type=state_dev.type,
        )
        props = []
        for p in state_dev.properties:
            seq_max = 0
            if core.isPropertySequenceable(state_dev.label, p.name):
                seq_max = core.getPropertySequenceMaxLength(
                    state_dev.label, p.name
                )
            props.append(
                DevicePropertySetting(
                    device_label=state_dev.label,
                    property_name=p.name,
                    value=p.value,
                    property_type=p.data_type,
                    is_read_only=p.is_read_only,
                    is_pre_init=p.is_pre_init,
                    allowed_values=p.allowed_values,
                    limits=p.limits,
                    sequence_max_length=seq_max,
                    device_type=state_dev.type,
                )
            )
        dev.properties = tuple(props)
        yield dev


def get_available_devices(
    core: CMMCorePlus, *, exclude: Container[tuple[str, str]] = ()
) -> Iterable[Device]:
    """Get all available devices, not just the loaded ones.

    Use `exclude` to filter out devices that should not be included (e.g. device for
    which you already have information from `get_loaded_devices()`):
    >>> from pymmcore_plus import CMMCorePlus
    >>> core = CMMCorePlus()
    >>> loaded = get_loaded_devices(core)
    >>> available = get_available_devices(core, exclude={dev.key() for dev in loaded})
    """
    for library in core.getDeviceAdapterNames():
        dev_names = core.getAvailableDevices(library)
        types = core.getAvailableDeviceTypes(library)
        descriptions = core.getAvailableDeviceDescriptions(library)
        for dev_name, description, dev_type in zip(
            dev_names, descriptions, types, strict=False
        ):
            if (library, dev_name) not in exclude:
                yield Device(
                    name=dev_name,
                    library=library,
                    description=description,
                    type=DeviceType(dev_type),
                )


# ---- internal conversion helpers ----


def _convert_preset(
    core: CMMCorePlus, state_preset: StateConfigPreset
) -> ConfigPreset:
    """Convert a state ConfigPreset to a widget ConfigPreset."""
    preset_model = ConfigPreset(name=state_preset.name)
    for s in state_preset.settings:
        setting = _convert_setting(core, s)
        setting.parent = preset_model
        preset_model.settings.append(setting)
    return preset_model


def _convert_setting(
    core: CMMCorePlus, s: PropertySetting
) -> DevicePropertySetting:
    """Convert a PropertySetting to a DevicePropertySetting with metadata."""
    prop = core_io.read_property_info(core, s.device, s.property)
    seq_max = 0
    if core.isPropertySequenceable(s.device, s.property):
        seq_max = core.getPropertySequenceMaxLength(s.device, s.property)
    return DevicePropertySetting(
        device_label=s.device,
        property_name=s.property,
        value=s.value,
        property_type=prop.data_type,
        is_read_only=prop.is_read_only,
        is_pre_init=prop.is_pre_init,
        allowed_values=prop.allowed_values,
        limits=prop.limits,
        sequence_max_length=seq_max,
        device_type=core.getDeviceType(s.device),
    )
