# Copyright (C) 2022 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR BSD-3-Clause


class TreeItem:
    def __init__(self, data: list, parent: "TreeItem" = None):
        self.item_data = data
        self.parent_item = parent
        self.child_items: list["TreeItem"] = []

    def setup(self, lines: list[str]):
        parents = [self]
        indentations = [0]

        for line in lines:
            line = line.rstrip()
            if line and "\t" in line:
                position = 0
                while position < len(line):
                    if line[position] != " ":
                        break
                    position += 1

                column_data = line[position:].split("\t")
                column_data = [string for string in column_data if string]
                if position > indentations[-1]:
                    if parents[-1].child_count() > 0:
                        parents.append(parents[-1].last_child())
                        indentations.append(position)
                else:
                    while position < indentations[-1] and parents:
                        parents.pop()
                        indentations.pop()

                parent: TreeItem = parents[-1]
                col_count = self.column_count()
                parent.insert_children(parent.child_count(), 1, col_count)

                for column in range(len(column_data)):
                    child = parent.last_child()
                    child.set_data(column, column_data[column])

    def child(self, number: int) -> "TreeItem":
        if number < 0 or number >= len(self.child_items):
            return None
        return self.child_items[number]

    def last_child(self):
        return self.child_items[-1] if self.child_items else None

    def child_count(self) -> int:
        return len(self.child_items)

    def child_number(self) -> int:
        if self.parent_item:
            return self.parent_item.child_items.index(self)
        return 0

    def column_count(self) -> int:
        return len(self.item_data)

    def data(self, column: int):
        if column < 0 or column >= len(self.item_data):
            return None
        return self.item_data[column]

    def insert_children(self, position: int, count: int, columns: int) -> bool:
        if position < 0 or position > len(self.child_items):
            return False

        for row in range(count):
            data = [None] * columns
            item = TreeItem(data.copy(), self)
            self.child_items.insert(position, item)

        return True

    def insert_columns(self, position: int, columns: int) -> bool:
        if position < 0 or position > len(self.item_data):
            return False

        for column in range(columns):
            self.item_data.insert(position, None)

        for child in self.child_items:
            child.insert_columns(position, columns)

        return True

    def parent(self):
        return self.parent_item

    def remove_children(self, position: int, count: int) -> bool:
        if position < 0 or position + count > len(self.child_items):
            return False

        for row in range(count):
            self.child_items.pop(position)

        return True

    def remove_columns(self, position: int, columns: int) -> bool:
        if position < 0 or position + columns > len(self.item_data):
            return False

        for column in range(columns):
            self.item_data.pop(position)

        for child in self.child_items:
            child.remove_columns(position, columns)

        return True

    def set_data(self, column: int, value):
        if column < 0 or column >= len(self.item_data):
            return False

        self.item_data[column] = value
        return True

    def __repr__(self) -> str:
        result = f"<treeitem.TreeItem at 0x{id(self):x}"
        for d in self.item_data:
            result += f' "{d}"' if d else " <None>"
        result += f", {len(self.child_items)} children>"
        return result
