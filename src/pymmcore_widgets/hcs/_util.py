from __future__ import annotations

from typing import TYPE_CHECKING

import useq
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QGraphicsScene, QGraphicsView, QWidget
from useq import WellPlate

if TYPE_CHECKING:
    from qtpy.QtGui import QResizeEvent


def _sort_plate_names(item: str) -> tuple[int, int | str]:
    """Sort well plate keys by number first, then by string."""
    parts = item.split("-")
    if parts[0].isdigit():
        return (0, int(parts[0]))
    return (1, item)


# our internal registry of known well plates
PLATES: dict[str, WellPlate] = {}

# sort the well plates by number first, then by string
for key in sorted(useq.registered_well_plate_keys(), key=_sort_plate_names):
    plate = useq.WellPlate.from_str(key)
    if not plate.name:
        plate = plate.replace(name=key)
    PLATES[key] = plate


class ResizingGraphicsView(QGraphicsView):
    """A QGraphicsView that resizes the scene to fit the view."""

    def __init__(self, scene: QGraphicsScene, parent: QWidget | None = None) -> None:
        super().__init__(scene, parent)

    def resizeEvent(self, event: QResizeEvent) -> None:
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
