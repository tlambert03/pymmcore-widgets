from __future__ import annotations

from qtpy.QtCore import QAbstractItemModel, QModelIndex, Qt
from qtpy.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QWidget

from mmcore_schema.state import PropertyInfo
from pymmcore_widgets.device_properties import PropertyWidget


class PropertySettingDelegate(QStyledItemDelegate):
    """Item delegate that uses a PropertyWidget for editing PropertySetting values."""

    def createEditor(
        self, parent: QWidget | None, option: QStyleOptionViewItem, index: QModelIndex
    ) -> QWidget | None:
        if not isinstance(
            (setting := index.data(Qt.ItemDataRole.UserRole)), PropertyInfo
        ):
            return super().createEditor(parent, option, index)  # pragma: no cover
        widget = PropertyWidget(
            setting.device_label,
            setting.name,
            parent=parent,
            connect_core=False,
        )
        widget.setValue(setting.value)  # avoids commitData warnings
        widget.valueChanged.connect(lambda: self.commitData.emit(widget))
        widget.setAutoFillBackground(True)
        return widget

    def setEditorData(self, editor: QWidget | None, index: QModelIndex) -> None:
        setting = index.data(Qt.ItemDataRole.UserRole)
        if isinstance(setting, PropertyInfo) and isinstance(
            editor, PropertyWidget
        ):
            editor.setValue(setting.value)
        else:  # pragma: no cover
            super().setEditorData(editor, index)

    def setModelData(
        self,
        editor: QWidget | None,
        model: QAbstractItemModel | None,
        index: QModelIndex,
    ) -> None:
        if model and isinstance(editor, PropertyWidget):
            model.setData(index, editor.value(), Qt.ItemDataRole.EditRole)
        else:  # pragma: no cover
            super().setModelData(editor, model, index)
