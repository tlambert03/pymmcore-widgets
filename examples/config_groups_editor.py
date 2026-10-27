"""ConfigGroupsEditor edits configuration groups and their presets.

It doesn't change the core: when you click "Apply", it emits `applyRequested`
with the changes, and it's up to you what to do with them.
"""

from pymmcore_plus import CMMCorePlus
from qtpy.QtWidgets import QApplication

from pymmcore_widgets import ConfigGroupsEditor

app = QApplication([])
core = CMMCorePlus.instance()
core.loadSystemConfiguration()

# load the core's devices, groups and presets into the editor
# (pass `load_configs=False` to start with an empty list of groups)
cfg = ConfigGroupsEditor.create_from_core(core)


# connect to apply signal to print the changes
def _on_apply_clicked(changed, deleted, channel_group):
    print("\n\nApply clicked:")
    print(f"Changed: {[cg.name for cg in changed]}")
    print(f"Deleted: {deleted}")
    print(f"Channel group: {channel_group}")


cfg.applyRequested.connect(_on_apply_clicked)

cfg.resize(900, 550)
cfg.show()

app.exec()
