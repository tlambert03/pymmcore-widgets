from mmcore_schema.state import ConfigGroup, DeviceInfo
from pymmcore_plus import CMMCorePlus


def test_get_loaded_devices() -> None:
    core = CMMCorePlus()
    core.loadSystemConfiguration()
    DeviceInfo.all_from_core(core)
    DeviceInfo.available_from_core(core)
    ConfigGroup.all_from_core(core)
