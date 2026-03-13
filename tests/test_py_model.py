from pymmcore_plus import CMMCorePlus
from pymmcore_plus.core_io import (
    read_available_devices,
    read_config_groups,
    read_devices,
)


def test_get_loaded_devices() -> None:
    core = CMMCorePlus()
    core.loadSystemConfiguration()
    read_devices(core)
    read_available_devices(core)
    read_config_groups(core)
