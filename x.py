from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QAbstractItemModel, QEvent
from click import edit
from pymmcore_plus import CMMCorePlus
from pymmcore_plus.model import Microscope
from qtpy.QtCore import QModelIndex, Qt
from qtpy.QtGui import QStandardItem, QStandardItemModel
from qtpy.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QListView,
    QSplitter,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableView,
    QWidget,
)

if TYPE_CHECKING:
    from PyQt6.QtGui import QPainter
    from qtpy.QtWidgets import QStyleOptionViewItem

try:
    CHECKED: int = int(Qt.CheckState.Checked.value)
except AttributeError:
    CHECKED = 2


class QScopeModel(QStandardItemModel):
    @classmethod
    def from_scope(cls, scope: Microscope | None = None) -> QScopeModel:
        if scope is None:
            scope = Microscope.create_from_core(CMMCorePlus.instance())

        model = cls()
        for config in scope.config_groups.values():
            group_item = QStandardItem(config.name)
            for preset in config.presets.values():
                preset_item = QStandardItem(preset.name)

                for dev, prop, val in preset.settings:
                    i0 = QStandardItem(f"{dev}-{prop}")
                    i0.setFlags(i0.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    i0.setData((dev, prop), Qt.ItemDataRole.UserRole)
                    i0.setCheckState(Qt.CheckState.Unchecked)
                    preset_item.appendRow([i0, QStandardItem(val)])

                group_item.appendRow(preset_item)
            model.appendRow(group_item)
        return model

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = 0
    ) -> Any:
        d = super().headerData(section, orientation, role)
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole:
                return ["Property", "Value"][section]
        return d


from pymmcore_widgets import PropertyWidget


class SettingsDelegate(QStyledItemDelegate):
    def setEditorData(self, editor: QWidget, index: QModelIndex) -> None:
        print("setEditorData", editor, index)
        if isinstance(editor, PropertyWidget) and index.column() == 1:
            val = index.model().data(index, Qt.ItemDataRole.DisplayRole)
            editor.setValue(val)
        else:
            super().setEditorData(editor, index)

    def editorEvent(
        self,
        event: QEvent | None,
        model: QAbstractItemModel | None,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> bool:
        print("editorEvent", event, model, option, index)
        return super().editorEvent(event, model, option, index)

    def setModelData(
        self, editor: QWidget, model: QStandardItemModel, index: QModelIndex
    ) -> None:
        print("setModelData", editor, model, index)
        if isinstance(editor, PropertyWidget) and index.column() == 1:
            model.setData(index, editor.value(), Qt.ItemDataRole.DisplayRole)
        else:
            super().setModelData(editor, model, index)

    def createEditor(
        self, parent: QWidget | None, option: QStyleOptionViewItem, index: QModelIndex
    ) -> QWidget | None:
        if index.column() == 1:
            dp = index.model().data(index.siblingAtColumn(0), Qt.ItemDataRole.UserRole)
            wdg = PropertyWidget(*dp, parent=parent, connect_core=False)
            wdg.valueChanged.connect(lambda: self.commitData.emit(wdg))
            return wdg
        return super().createEditor(parent, option, index)

    def paint(
        self, painter: QPainter | None, option: QStyleOptionViewItem, index: QModelIndex
    ) -> None:
        if index.data(Qt.ItemDataRole.CheckStateRole) == CHECKED:
            option.font.setBold(True)
        return super().paint(painter, option, index)


class Wdg(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self._groups = QListView()
        self._presets = QListView()
        self._settings = QTableView()
        self._settings.setItemDelegate(SettingsDelegate())

        model = QScopeModel.from_scope()
        self._groups.setModel(model)
        self._presets.setModel(model)
        self._settings.setModel(model)
        self._settings.verticalHeader().setVisible(False)
        hh = self._settings.horizontalHeader()
        hh.setStretchLastSection(True)

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
        self._settings.resizeColumnsToContents()
        for row in range(current.model().rowCount(current)):
            self._settings.openPersistentEditor(current.model().index(row, 1, current))


if __name__ == "__main__":
    core = CMMCorePlus.instance()
    core.loadSystemConfiguration()

    app = QApplication([])
    window = Wdg()
    window.show()
    app.exec()
