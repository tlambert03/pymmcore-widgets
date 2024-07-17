from __future__ import annotations

from pymmcore_plus import CMMCorePlus
from pymmcore_plus.model import Microscope
from qtpy.QtCore import QModelIndex, Qt
from qtpy.QtGui import QStandardItem, QStandardItemModel
from qtpy.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QListView,
    QSplitter,
    QTableView,
    QWidget,
)


def scope_model(prop_tree: bool = False) -> QStandardItemModel:
    core = CMMCorePlus.instance()
    scope = Microscope.create_from_core(core)
    model = QStandardItemModel()
    for config in scope.config_groups.values():
        group_item = QStandardItem(config.name)
        for preset in config.presets.values():
            preset_item = QStandardItem(preset.name)

            if prop_tree:
                _dpv: dict[str, dict[str, str]] = {}
                for dev, prop, val in preset.settings:
                    if dev not in _dpv:
                        _dpv[dev] = {}
                    _dpv[dev][prop] = val
                for dev, props in _dpv.items():
                    dev_item = QStandardItem(dev)
                    for prop, val in props.items():
                        i0 = QStandardItem(prop)
                        i0.setFlags(Qt.ItemFlag.ItemIsUserCheckable)
                        dev_item.appendRow([i0, QStandardItem(val)])
                    preset_item.appendRow(dev_item)
            else:
                for dev, prop, val in preset.settings:
                    preset_item.appendRow(
                        [QStandardItem(dev), QStandardItem(prop), QStandardItem(val)]
                    )

            group_item.appendRow(preset_item)
        model.appendRow(group_item)
    return model


class Wdg(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self._groups = QListView()
        self._presets = QListView()
        self._settings = QTableView()

        model = scope_model()
        self._groups.setModel(model)
        self._presets.setModel(model)
        self._settings.setModel(model)
        self._settings.setModel(model)

        left = QSplitter(Qt.Orientation.Vertical)
        left.addWidget(self._groups)
        left.addWidget(self._presets)

        layout = QHBoxLayout(self)
        layout.addWidget(left)
        layout.addWidget(self._settings)

        if preset_sel := self._presets.selectionModel():
            preset_sel.currentChanged.connect(self._on_preset_changed)

        if group_sel := self._groups.selectionModel():
            group_sel.currentChanged.connect(self._on_group_changed)
            group_sel.setCurrentIndex(
                model.index(0, 0, QModelIndex()), group_sel.SelectionFlag.SelectCurrent
            )

    def _on_group_changed(self, current: QModelIndex) -> None:
        self._presets.setRootIndex(current)
        if preset_sel := self._presets.selectionModel():
            if model := preset_sel.model():
                preset_sel.setCurrentIndex(
                    model.index(0, 0, current),
                    preset_sel.SelectionFlag.SelectCurrent,
                )

    def _on_preset_changed(self, current: QModelIndex) -> None:
        self._settings.setRootIndex(current)
        # self._settings.expandAll()


if __name__ == "__main__":
    core = CMMCorePlus.instance()
    core.loadSystemConfiguration()

    app = QApplication([])
    window = Wdg()
    window.show()
    app.exec()
