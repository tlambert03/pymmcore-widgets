from typing import Iterable

import useq
from qtpy.QtCore import QRect, QRectF, QSize, Qt, Signal
from qtpy.QtGui import QFont, QMouseEvent, QPainter, QPen
from qtpy.QtWidgets import (
    QAbstractGraphicsShapeItem,
    QGraphicsItem,
    QGraphicsScene,
    QWidget,
)
from superqt.utils import signals_blocked

from pymmcore_widgets._util import ResizingGraphicsView

DATA_POSITION = 1
DATA_INDEX = 2

# in the WellPlateView, any item that merely posses a brush color of SELECTED_COLOR
# IS a selected object.
SELECTED_COLOR = Qt.GlobalColor.green
UNSELECTED_COLOR = Qt.GlobalColor.transparent


class WellPlateView(ResizingGraphicsView):
    """QGraphicsView for displaying a well plate."""

    selectionChanged = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        self._scene = QGraphicsScene()
        super().__init__(self._scene, parent)
        self.setStyleSheet("background:grey; border-radius: 5px;")
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
        )
        # RubberBandDrag enables rubber band selection with mouse
        self.setDragMode(self.DragMode.RubberBandDrag)
        self.rubberBandChanged.connect(self._on_rubber_band_changed)

        # all the graphics items that outline wells
        self._well_items: list[QAbstractGraphicsShapeItem] = []
        # all the graphics items that label wells
        self._well_labels: list[QGraphicsItem] = []

        # we manually manage the selection state of items
        self._selected_items: set[QAbstractGraphicsShapeItem] = set()
        # the set of selected items at the time of the mouse press
        self._selection_on_press: set[QAbstractGraphicsShapeItem] = set()

        # item at the point where the mouse was pressed
        self._pressed_item: QAbstractGraphicsShapeItem | None = None
        # whether option/alt is pressed at the time of the mouse press
        self._is_removing = False

    def _on_rubber_band_changed(self, rect: QRect) -> None:
        """When the rubber band changes, select the items within the rectangle."""
        if rect.isNull():  # pragma: no cover
            # this is the last signal emitted when releasing the mouse
            return

        # all scene items within the rubber band
        bounded_items = set(self._scene.items(self.mapToScene(rect).boundingRect()))

        # loop through all wells and recolor them based on their selection state
        select = set()
        deselect = set()
        for item in self._well_items:
            if item in bounded_items:
                if self._is_removing:
                    deselect.add(item)
                else:
                    select.add(item)
            # if the item is not in the rubber band, keep its previous state
            elif item in self._selection_on_press:
                select.add(item)
            else:
                deselect.add(item)
        with signals_blocked(self):
            self._select_items(select)
        self._deselect_items(deselect)

    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        if (
            self.dragMode() != self.DragMode.NoDrag
            and event
            and event.button() == Qt.MouseButton.LeftButton
        ):
            # store the state of selected items at the time of the mouse press
            self._selection_on_press = self._selected_items.copy()

            # when the cmd/control key is pressed, add to the selection
            if event.modifiers() & Qt.KeyboardModifier.AltModifier:
                self._is_removing = True

            # store the item at the point where the mouse was pressed
            for item in self.items(event.pos()):
                if isinstance(item, QAbstractGraphicsShapeItem):
                    self._pressed_item = item
                    break
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent | None) -> None:
        if event and event.button() == Qt.MouseButton.LeftButton:
            # if we are on the same item that we pressed,
            # toggle selection of that item
            for item in self.items(event.pos()):
                if item == self._pressed_item:
                    if self._pressed_item.brush().color() == SELECTED_COLOR:
                        self._deselect_items((self._pressed_item,))
                    else:
                        self._select_items((self._pressed_item,))
                    break

        self._pressed_item = None
        self._is_removing = False
        self._selection_on_press.clear()
        super().mouseReleaseEvent(event)

    def selectedIndices(self) -> tuple[tuple[int, int], ...]:
        """Return the indices of the selected wells."""
        return tuple(sorted(item.data(DATA_INDEX) for item in self._selected_items))

    def setSelectedIndices(self, indices: Iterable[tuple[int, int]]) -> None:
        """Select the wells with the given indices.

        Parameters
        ----------
        indices : Iterable[tuple[int, int]]
            The indices of the wells to select. Each index is a tuple of row and column.
            e.g. [(0, 0), (1, 1), (2, 2)]
        """
        _indices = {tuple(idx) for idx in indices}
        select = set()
        deselect = set()
        for item in self._well_items:
            if item.data(DATA_INDEX) in _indices:
                select.add(item)
            else:
                deselect.add(item)
        with signals_blocked(self):
            self._select_items(select)
        self._deselect_items(deselect)

    def clearSelection(self) -> None:
        """Clear the current selection."""
        self._deselect_items(self._selected_items)

    def clear(self) -> None:
        """Clear all the wells from the view."""
        while self._well_items:
            self._scene.removeItem(self._well_items.pop())
        while self._well_labels:
            self._scene.removeItem(self._well_labels.pop())
        self.clearSelection()

    def drawPlate(self, plan: useq.WellPlate | useq.WellPlatePlan) -> None:
        """Draw the well plate on the view.

        Parameters
        ----------
        plan : useq.WellPlate | useq.WellPlatePlan
            The WellPlatePlan to draw. If a WellPlate is provided, the plate is drawn
            with no selected wells.
        """
        if isinstance(plan, useq.WellPlate):  # pragma: no cover
            plan = useq.WellPlatePlan(
                a1_center_xy=(0, 0), plate=plan, selected_wells=None
            )

        well_width = plan.plate.well_size[0] * 1000
        well_height = plan.plate.well_size[1] * 1000
        well_rect = QRectF(-well_width / 2, -well_height / 2, well_width, well_height)
        add_item = (
            self._scene.addEllipse if plan.plate.circular_wells else self._scene.addRect
        )

        # font for well labels
        font = QFont()
        font.setPixelSize(int(min(6000, well_rect.width() / 2.5)))

        # Since most plates have the same extent, a constant pen width seems to work
        pen = QPen(Qt.GlobalColor.black)
        pen.setWidth(200)

        self.clear()
        indices = plan.all_well_indices.reshape(-1, 2)
        for idx, pos in zip(indices, plan.all_well_positions):
            # invert y-axis for screen coordinates
            screen_x, screen_y = pos.x, -pos.y
            rect = well_rect.translated(screen_x, screen_y)
            if item := add_item(rect, pen):
                item.setData(DATA_POSITION, pos)
                item.setData(DATA_INDEX, tuple(idx.tolist()))
                if plan.rotation:
                    item.setTransformOriginPoint(rect.center())
                    item.setRotation(-plan.rotation)
                self._well_items.append(item)

            # NOTE, we are *not* using the Qt selection model here due to
            # customizations that we want to make.  So we don't use...
            # item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)

            # add text
            if text_item := self._scene.addText(pos.name):
                text_item.setFont(font)
                br = text_item.boundingRect()
                text_item.setPos(
                    screen_x - br.width() // 2,
                    screen_y - br.height() // 2,
                )
                self._well_labels.append(text_item)

        if plan.selected_wells:
            self.setSelectedIndices(plan.selected_well_indices)

        self._resize_to_fit()

    def _resize_to_fit(self) -> None:
        self.setSceneRect(self._scene.itemsBoundingRect())
        self.resizeEvent(None)

    def _select_items(self, items: Iterable[QAbstractGraphicsShapeItem]) -> None:
        for item in items:
            item.setBrush(SELECTED_COLOR)
        self._selected_items.update(items)
        self.selectionChanged.emit()

    def _deselect_items(self, items: Iterable[QAbstractGraphicsShapeItem]) -> None:
        for item in items:
            item.setBrush(UNSELECTED_COLOR)
        self._selected_items.difference_update(items)
        self.selectionChanged.emit()

    def sizeHint(self) -> QSize:
        """Provide a reasonable size hint with aspect ratio of a well plate."""
        aspect = 1.5
        width = 600
        height = int(width // aspect)
        return QSize(width, height)
