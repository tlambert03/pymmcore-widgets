"""Wizard-local device and model classes.

These replace the dependency on pymmcore_plus.model (Microscope, Device, etc.)
for the hardware configuration wizard, using mmcore_schema.MMConfig for file I/O
and pymmcore_plus.core_io for device reads.
"""

from __future__ import annotations

import dataclasses
import os
from contextlib import suppress
from copy import deepcopy
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pymmcore_plus import (
    CMMCorePlus,
    DeviceInitializationState,
    DeviceType,
    FocusDirection,
    Keyword,
    PropertyType,
    core_io,
)
from pymmcore_plus._util import no_stdout

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

UNDEFINED = "UNDEFINED"
CORE = Keyword.CoreDevice.value


# ----------- Property -----------


@dataclass
class Property:
    """A device property."""

    device_name: str
    name: str
    value: str = ""
    is_read_only: bool = False
    is_pre_init: bool = False
    allowed_values: tuple[str, ...] = ()
    has_limits: bool = False
    lower_limit: float = 0.0
    upper_limit: float = 0.0
    property_type: PropertyType = PropertyType.Undef


# ----------- Device -----------


@dataclass
class Device:
    """A device in the wizard's model."""

    name: str = UNDEFINED
    library: str = ""
    adapter_name: str = ""
    description: str = ""
    device_type: DeviceType = DeviceType.Any
    properties: list[Property] = field(default_factory=list)
    delay_ms: float = 0.0
    uses_delay: bool = False
    parent_label: str = ""
    initialized: bool = False
    # StateDevice
    labels: tuple[str, ...] = field(default_factory=tuple)
    # StageDevice
    focus_direction: FocusDirection = FocusDirection.Unknown
    # HubDevice — adapter names of available children
    children: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.name == Keyword.CoreDevice or self.device_type == DeviceType.Core:
            raise ValueError(
                "Cannot create a Device with type Core. Use CoreDevice instead."
            )
        if self.name == UNDEFINED and self.device_type == DeviceType.Serial:
            self.name = self.adapter_name

    def __hash__(self) -> int:
        return id(self)

    @property
    def port(self) -> str | None:
        """Value of the Port property, or None."""
        return next((p.value for p in self.properties if p.name == Keyword.Port), None)

    def get_property(self, name: str) -> Property:
        for prop in self.properties:
            if prop.name == name:
                return prop
        raise ValueError(f"Device {self.name!r} has no property {name!r}.")

    def set_property(self, prop_name: str, value: Any) -> None:
        self.get_property(prop_name).value = str(value)

    def set_prop_default(
        self, prop_name: str, value: str = "", **kwargs: Any
    ) -> Property:
        """Add a property if it doesn't exist, otherwise return existing."""
        try:
            return self.get_property(prop_name)
        except ValueError:
            prop = Property(self.name, str(prop_name), value, **kwargs)
            self.properties.append(prop)
            return prop

    def set_label(self, state: int | str, label: str) -> None:
        try:
            state = int(state)
        except (ValueError, TypeError):
            raise ValueError(f"State {state!r} is not an integer") from None
        lst = list(self.labels)
        if state >= len(lst):
            lst.extend(f"State-{i}" for i in range(len(lst), state + 1))
        lst[state] = label
        self.labels = tuple(lst)

    def replace(self, **kwargs: Any) -> Device:
        return dataclasses.replace(self, **kwargs)

    # --- core interaction ---

    @classmethod
    def create_from_core(
        cls, core: CMMCorePlus, *, name: str, initialized: bool = False
    ) -> Device:
        """Create a Device by reading its state from core."""
        info = core_io.read_device_info(core, name)
        dev = cls(
            name=info.label,
            library=info.library,
            adapter_name=info.name,
            description=info.description,
            device_type=DeviceType(int(info.type)),
            delay_ms=core.getDeviceDelayMs(name),
            uses_delay=core.usesDeviceDelay(name),
            parent_label=info.parent_label,
            initialized=initialized,
            labels=info.state_labels,
            focus_direction=info.focus_direction,
            children=info.child_names,
        )
        dev.properties = _properties_from_info(name, info.properties)
        return dev

    def update_from_core(self, core: CMMCorePlus) -> None:
        """Refresh device state from core."""
        info = core_io.read_device_info(core, self.name)
        self.library = info.library
        self.adapter_name = info.name
        self.description = info.description
        self.device_type = DeviceType(int(info.type))
        self.delay_ms = core.getDeviceDelayMs(self.name)
        self.uses_delay = core.usesDeviceDelay(self.name)
        self.parent_label = info.parent_label
        self.labels = info.state_labels
        self.focus_direction = info.focus_direction
        self.children = info.child_names
        self.properties = _properties_from_info(self.name, info.properties)

    def load(self, core: CMMCorePlus, *, reload: bool = False) -> None:
        """Load device into core."""
        if reload and self.name in core.getLoadedDevices():
            core.unloadDevice(self.name)
        core.loadDevice(self.name, self.library, self.adapter_name)
        self.initialized = False

    def initialize(
        self,
        core: CMMCorePlus,
        *,
        apply_pre_init: bool = False,
        reload: bool = False,
    ) -> None:
        """Initialize device in core."""
        if reload:
            self.load(core, reload=reload)
        if apply_pre_init:
            for prop in self.properties:
                if prop.is_pre_init:
                    prop_apply_to_core(prop, core)
        core.initializeDevice(self.name)
        self.initialized = True
        self.apply_to_core(core)

    def apply_to_core(self, core: CMMCorePlus) -> None:
        """Apply device settings to core."""
        with suppress(RuntimeError):
            if self.delay_ms:
                core.setDeviceDelayMs(self.name, self.delay_ms)
        with suppress(RuntimeError):
            if self.parent_label:
                core.setParentLabel(self.name, self.parent_label)
        if self.device_type == DeviceType.State:
            for state, label in enumerate(self.labels):
                with suppress(RuntimeError):
                    core.defineStateLabel(self.name, state, label)
        elif self.device_type == DeviceType.Stage:
            with suppress(RuntimeError):
                core.setFocusDirection(self.name, self.focus_direction)
        for prop in self.properties:
            if not prop.is_pre_init:
                prop_apply_to_core(prop, core)
        self.update_from_core(core)

    def available_peripherals(self, model: WizardModel) -> Iterable[AvailableDevice]:
        """Yield available hub children not yet in the model."""
        if self.device_type != DeviceType.Hub:
            raise ValueError(f"Device {self.name} is not a Hub.")
        for dev in model.available_devices:
            if (
                (hub := dev.library_hub)
                and hub.library == self.library
                and hub.adapter_name == self.adapter_name
                and not any(
                    model.filter_devices(
                        library=dev.library,
                        adapter_name=dev.adapter_name,
                        parent_label=self.name,
                    )
                )
            ):
                yield dev


@dataclass
class AvailableDevice(Device):
    """An available (not yet loaded) device, possibly a hub child."""

    library_hub: AvailableDevice | None = None

    def __hash__(self) -> int:
        return super().__hash__()


# ----------- CoreDevice -----------


def _core_prop(name: str, val: str = "") -> Property:
    return Property(CORE, str(name), value=val, is_read_only=False)


def _core_props() -> list[Property]:
    return [
        _core_prop(Keyword.CoreAutoShutter, "1"),
        _core_prop(Keyword.CoreCamera),
        _core_prop(Keyword.CoreShutter),
        _core_prop(Keyword.CoreFocus),
        _core_prop(Keyword.CoreXYStage),
        _core_prop(Keyword.CoreAutoFocus),
        _core_prop(Keyword.CoreImageProcessor),
        _core_prop(Keyword.CoreSLM),
        _core_prop(Keyword.CoreGalvo),
        _core_prop(Keyword.CoreChannelGroup),
        _core_prop(Keyword.CoreTimeoutMs),
    ]


@dataclass
class CoreDevice(Device):
    """The Core device, holding role assignments."""

    name: str = CORE
    adapter_name: str = CORE
    device_type: DeviceType = DeviceType.Core
    description: str = "Core device"
    properties: list[Property] = field(default_factory=_core_props)

    def __post_init__(self) -> None:
        pass  # bypass Device validation

    def __hash__(self) -> int:
        return super().__hash__()

    def apply_to_core(self, core: CMMCorePlus) -> None:
        for prop in self.properties:
            if prop.name != Keyword.CoreInitialize:
                with suppress(RuntimeError):
                    core.setProperty(self.name, prop.name, prop.value)

    def update_from_core(self, core: CMMCorePlus) -> None:
        for prop in self.properties:
            with suppress(RuntimeError):
                prop.value = core.getProperty(CORE, prop.name)


# ----------- WizardModel -----------


@dataclass
class WizardModel:
    """Mutable model for the hardware configuration wizard.

    Replaces pymmcore_plus.model.Microscope.
    """

    core_device: CoreDevice = field(default_factory=CoreDevice)
    devices: list[Device] = field(default_factory=list)
    config_file: str = ""
    initialized: bool = False

    def __post_init__(self) -> None:
        self._available_devices: tuple[AvailableDevice, ...] = ()
        self._compare_state: WizardModel | None = None
        # Pass-through data from loaded config (for saving)
        self._mmconfig_extras: dict[str, Any] = {}

    @property
    def available_devices(self) -> tuple[AvailableDevice, ...]:
        return self._available_devices

    @property
    def available_serial_devices(self) -> Iterable[Device]:
        for dev in self.available_devices:
            if dev.device_type == DeviceType.Serial:
                yield dev

    @property
    def assigned_com_ports(self) -> dict[Device, Device]:
        """Map of SerialDevice -> DeviceUsingIt."""
        assigned: dict[Device, Device] = {}
        com_devices = {d.name: d for d in self.available_serial_devices}
        for dev in self.devices:
            if dev.port in com_devices:
                assigned[com_devices[dev.port]] = dev
        return assigned

    def reset(self) -> None:
        """Reset to an empty state (preserves available_devices)."""
        defaults = WizardModel()
        for f in fields(self):
            if f.name != "config_file":
                setattr(self, f.name, getattr(defaults, f.name))
        # Don't clear _available_devices — they're loaded once at wizard start
        self._mmconfig_extras = {}

    def is_dirty(self) -> bool:
        return self != (self._compare_state or WizardModel())

    def mark_clean(self) -> None:
        self._compare_state = deepcopy(self)

    def get_device(self, name: str) -> Device:
        for dev in self.devices:
            if dev.name == name:
                return dev
        raise KeyError(f"Device {name!r} not found")

    def filter_devices(
        self,
        name: str | None = None,
        library: str | None = None,
        adapter_name: str | None = None,
        description: str | None = None,
        device_type: DeviceType | str | None = None,
        parent_label: str | None = None,
    ) -> Iterable[Device]:
        if isinstance(device_type, str):
            device_type = DeviceType[device_type]
        if name == Keyword.CoreDevice.value or device_type == DeviceType.Core:
            yield self.core_device
            return

        criteria = {k: v for k, v in locals().items() if k != "self" and v is not None}
        for dev in self.devices:
            if all(getattr(dev, attr) == val for attr, val in criteria.items()):
                yield dev

    # --- File I/O ---

    def load_config(self, path: str | Path) -> None:
        """Load configuration from a .cfg file."""
        from mmcore_schema import MMConfig

        if not os.path.isfile(path):
            raise FileNotFoundError(f"Config file not found: {path}")

        fpath = Path(path).expanduser().resolve()
        self.config_file = str(fpath)
        mm = MMConfig.from_file(fpath)
        self.reset()
        self.config_file = str(fpath)  # reset clears this indirectly

        # Store pass-through data for saving
        self._mmconfig_extras = {
            "startup_configuration": mm.startup_configuration,
            "shutdown_configuration": mm.shutdown_configuration,
            "configuration_groups": mm.configuration_groups,
            "pixel_size_configurations": mm.pixel_size_configurations,
        }

        # Build parent_label→parent mapping from children fields
        parent_map: dict[str, str] = {}
        for cfg_dev in mm.devices:
            for child_label in cfg_dev.children:
                parent_map[child_label] = cfg_dev.label

        # Convert MMConfig.Devices → WizardModel.Device
        for cfg_dev in mm.devices:
            dev = Device(
                name=cfg_dev.label,
                library=cfg_dev.library,
                adapter_name=cfg_dev.name,
                parent_label=parent_map.get(cfg_dev.label, ""),
            )
            for p in cfg_dev.pre_init_properties:
                dev.properties.append(
                    Property(cfg_dev.label, p.property, p.value, is_pre_init=True)
                )
            for p in cfg_dev.post_init_properties:
                dev.properties.append(
                    Property(cfg_dev.label, p.property, p.value, is_pre_init=False)
                )
            if cfg_dev.delay_ms is not None:
                dev.delay_ms = cfg_dev.delay_ms
            if cfg_dev.focus_direction is not None:
                dev.device_type = DeviceType.Stage
                dev.focus_direction = FocusDirection(cfg_dev.focus_direction)
            if cfg_dev.state_labels:
                dev.device_type = DeviceType.State
                max_state = max(int(k) for k in cfg_dev.state_labels)
                lbls = [""] * (max_state + 1)
                for k, v in cfg_dev.state_labels.items():
                    lbls[int(k)] = v
                dev.labels = tuple(lbls)
            if cfg_dev.children:
                dev.device_type = DeviceType.Hub
            self.devices.append(dev)

        # Apply startup configuration to core device
        for setting in mm.startup_configuration:
            if setting.device == CORE:
                prop = self.core_device.set_prop_default(setting.property)
                prop.value = setting.value

    def save(self, path: str | Path) -> None:
        """Save configuration to a .cfg file using MMConfig."""
        from mmcore_schema import MMConfig as _MMConfig
        from mmcore_schema._primitives import PropertySetting as _PS

        path = Path(path)

        # Build parent→children map from device parent_label
        children_map: dict[str, list[str]] = {}
        for dev in self.devices:
            if dev.parent_label:
                children_map.setdefault(dev.parent_label, []).append(dev.name)

        # Build device list: serial ports first, then regular devices
        cfg_devices = []
        seen_labels: set[str] = set()
        for dev in (*self.assigned_com_ports, *self.devices):
            if dev.name in seen_labels:
                continue
            seen_labels.add(dev.name)
            cfg_devices.append(_device_to_mmconfig(dev, children_map.get(dev.name)))

        # Build startup configuration: start with stored, merge core roles
        startup = list(self._mmconfig_extras.get("startup_configuration", []))
        for prop in self.core_device.properties:
            key = (CORE, str(prop.name))
            found = False
            for i, s in enumerate(startup):
                if (s.device, s.property) == key:
                    if prop.value:
                        startup[i] = _PS(
                            device=CORE,
                            property=str(prop.name),
                            value=prop.value,
                        )
                    found = True
                    break
            if not found and prop.value:
                startup.append(
                    _PS(device=CORE, property=str(prop.name), value=prop.value)
                )

        mm = _MMConfig(
            devices=cfg_devices,
            startup_configuration=startup,
            shutdown_configuration=list(
                self._mmconfig_extras.get("shutdown_configuration", [])
            ),
            configuration_groups=list(
                self._mmconfig_extras.get("configuration_groups", [])
            ),
            pixel_size_configurations=list(
                self._mmconfig_extras.get("pixel_size_configurations", [])
            ),
        )
        mm.write_file(path)
        self.mark_clean()

    # --- Core interaction ---

    def load_available_devices(self, core: CMMCorePlus) -> None:
        self._available_devices = tuple(_get_available_devices(core))

    def initialize(
        self,
        core: CMMCorePlus,
        on_fail: Callable[[Device, BaseException], bool | None] | None = None,
    ) -> None:
        """Initialize all devices in core."""

        def _sort_key(d: Device) -> int:
            return {DeviceType.Serial: 0, DeviceType.Hub: 1}.get(d.device_type, 2)

        devs = sorted((*self.assigned_com_ports, *self.devices), key=_sort_key)
        for device in devs:
            if device.device_type == DeviceType.Core:
                continue
            try:
                device.initialize(core, reload=True, apply_pre_init=True)
            except Exception as e:
                if on_fail and on_fail(device, e):
                    return

    @classmethod
    def create_from_core(cls, core: CMMCorePlus) -> WizardModel:
        """Create model from current core state (for tests)."""
        model = cls()
        model.devices = [
            Device.create_from_core(core, name=name, initialized=True)
            for name in core.getLoadedDevices()
            if name != Keyword.CoreDevice
        ]
        model.core_device.update_from_core(core)
        model.load_available_devices(core)
        model.mark_clean()
        return model


# ----------- Helpers -----------


def _properties_from_info(
    device_name: str,
    props: tuple[Any, ...],
) -> list[Property]:
    """Convert PropertyInfo tuple to Property list."""
    return [
        Property(
            device_name=device_name,
            name=p.name,
            value=p.value,
            is_read_only=p.is_read_only,
            is_pre_init=p.is_pre_init,
            allowed_values=p.allowed_values,
            has_limits=p.limits is not None,
            lower_limit=p.limits[0] if p.limits else 0.0,
            upper_limit=p.limits[1] if p.limits else 0.0,
            property_type=p.data_type,
        )
        for p in props
    ]


def prop_apply_to_core(prop: Property, core: CMMCorePlus) -> None:
    """Apply a single property to core, ignoring errors."""
    try:
        core.setProperty(prop.device_name, prop.name, prop.value)
    except Exception:
        pass


def _device_to_mmconfig(dev: Device, child_labels: list[str] | None = None) -> Any:
    """Convert a WizardModel Device to an MMConfig Device."""
    from mmcore_schema.mmconfig import Device as _CfgDev
    from mmcore_schema.mmconfig import PropertyValue as _PV

    # Only save pre-init properties (the original wizard doesn't save post-init)
    pre = [_PV(property=p.name, value=p.value) for p in dev.properties if p.is_pre_init]

    state_labels: dict[str, str] = {}
    if dev.device_type == DeviceType.State and dev.labels:
        for i, label in enumerate(dev.labels):
            if label:
                state_labels[str(i)] = label

    focus_dir = None
    if dev.device_type == DeviceType.Stage:
        focus_dir = dev.focus_direction.value

    return _CfgDev(
        label=dev.name,
        library=dev.library,
        name=dev.adapter_name,
        pre_init_properties=pre,
        delay_ms=dev.delay_ms if dev.delay_ms else None,
        focus_direction=focus_dir,
        state_labels=state_labels,
        children=child_labels or [],
    )


def _get_available_devices(core: CMMCorePlus) -> list[AvailableDevice]:
    """Discover all available devices from adapter libraries."""
    available: list[AvailableDevice] = []
    library_to_hub: dict[tuple[str, str], AvailableDevice] = {}

    for lib_name in core.getDeviceAdapterNames():
        with suppress(RuntimeError):
            with no_stdout():
                devs = core.getAvailableDevices(lib_name)
            types = core.getAvailableDeviceTypes(lib_name)
            descriptions = core.getAvailableDeviceDescriptions(lib_name)
            for dev_name, dev_type, desc in zip(
                devs, types, descriptions, strict=False
            ):
                dev = AvailableDevice(
                    library=lib_name,
                    adapter_name=dev_name,
                    description=desc,
                    device_type=DeviceType(dev_type),
                )
                available.append(dev)
                if dev.device_type == DeviceType.Hub:
                    library_to_hub[(lib_name, dev_name)] = dev

    # Associate non-hub devices with their hub parents
    for d in available:
        if d.device_type != DeviceType.Hub:
            d.library_hub = library_to_hub.get((d.library, d.adapter_name))

    # Add child devices of loaded hubs
    for hub_label in core.getLoadedDevicesOfType(DeviceType.Hub):
        lib_name = core.getDeviceLibrary(hub_label)
        hub_dev = library_to_hub.get((lib_name, hub_label))
        if (
            core.getDeviceInitializationState(hub_label)
            != DeviceInitializationState.InitializedSuccessfully
        ):
            continue
        for child in core.getInstalledDevices(hub_label):
            dev = AvailableDevice(
                library=lib_name, adapter_name=child, library_hub=hub_dev
            )
            available.append(dev)

    return available
