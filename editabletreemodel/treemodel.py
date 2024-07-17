# Copyright (C) 2022 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR BSD-3-Clause
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from qtpy.QtCore import QModelIndex, Qt, QAbstractItemModel
# from treeitem import TreeItem


@dataclass
class TreeItem:
    data: list[Any] = field(default_factory=list)
    parent: TreeItem | None = None
    children: list["TreeItem"] = field(default_factory=list)

    def index_in_parent(self) -> int:
        if self.parent:
            return self.parent.children.index(self)
        return 0

    def column_count(self) -> int:
        return len(self.data)

    def insert_children(self, position: int, count: int, columns: int) -> bool:
        if position < 0 or position > len(self.children):
            return False

        for row in range(count):
            item = TreeItem("", self)
            self.children.insert(position, item)

        return True


root = TreeItem()
for x in range(3):
    group = TreeItem([f"group{x}"], parent=root)
    for i in range(6):
        preset = TreeItem([f"preset{i}"], parent=group)
        for j in range(4):
            setting = TreeItem([f"dev{i}", "prop", "value"], parent=preset)
            preset.children.append(setting)
        group.children.append(preset)
    root.children.append(group)

NULL = QModelIndex()


class TreeModel(QAbstractItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.root_item = root

    def columnCount(self, parent: QModelIndex = None) -> int:
        return 3

    def rowCount(self, parent: QModelIndex = NULL) -> int:
        if parent.isValid() and parent.column() > 0:
            return 0

        parent_item = self.get_item(parent)
        if parent_item:
            return len(parent_item.children)
        return 0

    def index(self, row: int, column: int, parent: QModelIndex = NULL) -> QModelIndex:
        if parent.isValid() and parent.column() != 0:
            return QModelIndex()

        parent_item: TreeItem = self.get_item(parent)
        if not parent_item:
            return QModelIndex()

        child_item: TreeItem = parent_item.children[row]
        if child_item:
            return self.createIndex(row, column, child_item)
        return QModelIndex()

    def parent(self, index: QModelIndex = NULL) -> QModelIndex:  # type: ignore [override]
        if not index.isValid():
            return QModelIndex()

        parent_item: TreeItem | None = self.get_item(index).parent
        if parent_item == self.root_item or not parent_item:
            return QModelIndex()

        return self.createIndex(parent_item.index_in_parent(), 0, parent_item)

    def data(self, index: QModelIndex, role: int | None = None) -> Any:
        if not index.isValid():
            return None

        if role != Qt.ItemDataRole.DisplayRole and role != Qt.ItemDataRole.EditRole:
            return None

        try:
            return self.get_item(index).data[index.column()]
        except IndexError:
            return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags

        return Qt.ItemFlag.ItemIsEditable | QAbstractItemModel.flags(self, index)

    def get_item(self, index: QModelIndex = QModelIndex()) -> TreeItem:
        if index.isValid() and (item := index.internalPointer()):
            return item
        return self.root_item

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
            and section < len(self.root_item.data)
        ):
            return self.root_item.data[section]

        return None

    def insertColumns(
        self, position: int, columns: int, parent: QModelIndex = QModelIndex()
    ) -> bool:
        self.beginInsertColumns(parent, position, position + columns - 1)
        success: bool = self.root_item.insert_columns(position, columns)
        self.endInsertColumns()

        return success

    def insertRows(
        self, position: int, rows: int, parent: QModelIndex = QModelIndex()
    ) -> bool:
        parent_item: TreeItem = self.get_item(parent)
        if not parent_item:
            return False

        self.beginInsertRows(parent, position, position + rows - 1)
        column_count = self.root_item.column_count()
        success: bool = parent_item.insert_children(position, rows, column_count)
        self.endInsertRows()

        return success

    def removeColumns(
        self, position: int, columns: int, parent: QModelIndex = QModelIndex()
    ) -> bool:
        self.beginRemoveColumns(parent, position, position + columns - 1)
        success: bool = self.root_item.remove_columns(position, columns)
        self.endRemoveColumns()

        if self.root_item.column_count() == 0:
            self.removeRows(0, self.rowCount())

        return success

    def removeRows(
        self, position: int, rows: int, parent: QModelIndex = QModelIndex()
    ) -> bool:
        parent_item: TreeItem = self.get_item(parent)
        if not parent_item:
            return False

        self.beginRemoveRows(parent, position, position + rows - 1)
        success: bool = parent_item.remove_children(position, rows)
        self.endRemoveRows()

        return success

    def setData(self, index: QModelIndex, value, role: int) -> bool:
        if role != Qt.ItemDataRole.EditRole:
            return False

        item: TreeItem = self.get_item(index)
        result: bool = item.set_data(index.column(), value)

        if result:
            self.dataChanged.emit(
                index, index, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole]
            )

        return result

    def setHeaderData(
        self, section: int, orientation: Qt.Orientation, value, role: int = None
    ) -> bool:
        if role != Qt.ItemDataRole.EditRole or orientation != Qt.Orientation.Horizontal:
            return False

        result: bool = self.root_item.set_data(section, value)

        if result:
            self.headerDataChanged.emit(orientation, section, section)

        return result

    def _repr_recursion(self, item: TreeItem, indent: int = 0) -> str:
        result = " " * indent + repr(item) + "\n"
        for child in item.child_items:
            result += self._repr_recursion(child, indent + 2)
        return result

    def __repr__(self) -> str:
        return self._repr_recursion(self.root_item)
