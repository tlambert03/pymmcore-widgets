# Copyright (C) 2022 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR BSD-3-Clause

import sys

from qtpy.QtCore import QAbstractItemModel, QItemSelectionModel, QModelIndex, Qt, Slot
from qtpy.QtTest import QAbstractItemModelTester
from qtpy.QtWidgets import (
    QHBoxLayout,
    QListView,
    QMainWindow,
    QTableView,
    QTreeView,
    QVBoxLayout,
    QWidget,
)
from treemodel import TreeModel


class MainWindow(QMainWindow):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.resize(573, 468)

        self.model = TreeModel(self)

        self.tree = QTreeView()
        self.tree.setModel(self.model)

        self.list = QListView()
        self.list.setModel(self.model)

        self.list2 = QListView()
        self.list2.setModel(self.model)
        self.list.selectionModel().currentChanged.connect(self.list2.setRootIndex)

        self.table = QTableView()
        self.table.setModel(self.model)
        self.list2.selectionModel().currentChanged.connect(self.table.setRootIndex)

        v = QVBoxLayout()
        v.addWidget(self.list)
        v.addWidget(self.list2)

        wdg = QWidget()
        layout = QHBoxLayout(wdg)

        layout.addWidget(self.tree)
        layout.addLayout(v)
        layout.addWidget(self.table)
        self.setCentralWidget(wdg)

        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        self.exit_action = file_menu.addAction("E&xit")
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.triggered.connect(self.close)

        actions_menu = menubar.addMenu("&Actions")
        actions_menu.triggered.connect(self.update_actions)
        self.insert_row_action = actions_menu.addAction("Insert Row")
        self.insert_row_action.setShortcut("Ctrl+I, R")
        self.insert_row_action.triggered.connect(self.insert_row)
        self.insert_column_action = actions_menu.addAction("Insert Column")
        self.insert_column_action.setShortcut("Ctrl+I, C")
        self.insert_column_action.triggered.connect(self.insert_column)
        actions_menu.addSeparator()
        self.remove_row_action = actions_menu.addAction("Remove Row")
        self.remove_row_action.setShortcut("Ctrl+R, R")
        self.remove_row_action.triggered.connect(self.remove_row)
        self.remove_column_action = actions_menu.addAction("Remove Column")
        self.remove_column_action.setShortcut("Ctrl+R, C")
        self.remove_column_action.triggered.connect(self.remove_column)
        actions_menu.addSeparator()
        self.insert_child_action = actions_menu.addAction("Insert Child")
        self.insert_child_action.setShortcut("Ctrl+N")
        self.insert_child_action.triggered.connect(self.insert_child)

        if "-t" in sys.argv:
            QAbstractItemModelTester(self.model, self)

        self.tree.expandAll()

        for column in range(self.model.columnCount()):
            self.tree.resizeColumnToContents(column)

        selection_model = self.tree.selectionModel()
        selection_model.selectionChanged.connect(self.update_actions)

        self.update_actions()

    @Slot()
    def insert_child(self) -> None:
        selection_model = self.tree.selectionModel()
        index: QModelIndex = selection_model.currentIndex()
        model: QAbstractItemModel = self.tree.model()

        if model.columnCount(index) == 0:
            if not model.insertColumn(0, index):
                return

        if not model.insertRow(0, index):
            return

        for column in range(model.columnCount(index)):
            child: QModelIndex = model.index(0, column, index)
            model.setData(child, "[No data]", Qt.EditRole)
            if not model.headerData(column, Qt.Horizontal):
                model.setHeaderData(column, Qt.Horizontal, "[No header]", Qt.EditRole)

        selection_model.setCurrentIndex(
            model.index(0, 0, index), QItemSelectionModel.ClearAndSelect
        )
        self.update_actions()

    @Slot()
    def insert_column(self) -> None:
        model: QAbstractItemModel = self.tree.model()
        column: int = self.tree.selectionModel().currentIndex().column()

        changed: bool = model.insertColumn(column + 1)
        if changed:
            model.setHeaderData(column + 1, Qt.Horizontal, "[No header]", Qt.EditRole)

        self.update_actions()

    @Slot()
    def insert_row(self) -> None:
        index: QModelIndex = self.tree.selectionModel().currentIndex()
        model: QAbstractItemModel = self.tree.model()
        parent: QModelIndex = index.parent()

        if not model.insertRow(index.row() + 1, parent):
            return

        self.update_actions()

        for column in range(model.columnCount(parent)):
            child: QModelIndex = model.index(index.row() + 1, column, parent)
            model.setData(child, "[No data]", Qt.EditRole)

    @Slot()
    def remove_column(self) -> None:
        model: QAbstractItemModel = self.tree.model()
        column: int = self.tree.selectionModel().currentIndex().column()

        if model.removeColumn(column):
            self.update_actions()

    @Slot()
    def remove_row(self) -> None:
        index: QModelIndex = self.tree.selectionModel().currentIndex()
        model: QAbstractItemModel = self.tree.model()

        if model.removeRow(index.row(), index.parent()):
            self.update_actions()

    @Slot()
    def update_actions(self) -> None:
        selection_model = self.tree.selectionModel()
        has_selection: bool = not selection_model.selection().isEmpty()
        self.remove_row_action.setEnabled(has_selection)
        self.remove_column_action.setEnabled(has_selection)

        current_index = selection_model.currentIndex()
        has_current: bool = current_index.isValid()
        self.insert_row_action.setEnabled(has_current)
        self.insert_column_action.setEnabled(has_current)

        if has_current:
            self.tree.closePersistentEditor(current_index)
            msg = f"Position: ({current_index.row()},{current_index.column()})"
            if not current_index.parent().isValid():
                msg += " in top level"
            self.statusBar().showMessage(msg)
