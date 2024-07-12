from __future__ import annotations

from typing import TYPE_CHECKING, Mapping

import useq
from qtpy.QtCore import Signal
from qtpy.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from superqt.utils import signals_blocked

from pymmcore_widgets.useq_widgets._well_plate_view import WellPlateView

if TYPE_CHECKING:
    Index = int | list[int] | tuple[int] | slice
    IndexExpression = tuple[Index, ...] | Index


def _sort_plate(item: str) -> tuple[int, int | str]:
    """Sort well plate keys by number first, then by string."""
    parts = item.split("-")
    if parts[0].isdigit():
        return (0, int(parts[0]))
    return (1, item)


class WellPlatePlanWidget(QWidget):
    """Widget for selecting a well plate and a subset of wells.

    The value returned/received by this widget is a [useq.WellPlatePlan][] (or simply
    a [useq.WellPlate][] if no selection is made).  This widget draws the well plate
    and allows the user to select wells by clicking/dragging on them.

    Parameters
    ----------
    plan: useq.WellPlatePlan | useq.WellPlate | None, optional
        The initial well plate plan. Accepts both a useq.WellPlate (which lacks a
        selection definition), or a full WellPlatePlan. By default None.
    parent : QWidget, optional
        The parent widget, by default None
    """

    valueChanged = Signal(object)

    def __init__(
        self,
        plan: useq.WellPlatePlan | useq.WellPlate | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._plate: useq.WellPlate | None = None
        self._a1_center_xy: tuple[float, float] = (0.0, 0.0)
        self._rotation: float | None = None

        # WIDGETS ---------------------------------------

        # well plate combobox
        self.plate_name = QComboBox()
        plate_names = sorted(useq.registered_well_plate_keys(), key=_sort_plate)
        self.plate_name.addItems(plate_names)

        # clear selection button
        self._clear_button = QPushButton(text="Clear Selection")
        self._clear_button.setAutoDefault(False)

        # plate view
        self._view = WellPlateView(self)

        self._show_rotation = QCheckBox("Show Rotation", self._view)
        self._show_rotation.move(6, 6)
        self._show_rotation.hide()

        # LAYOUT ---------------------------------------

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addWidget(QLabel("WellPlate:"), 0)
        top_layout.addWidget(self.plate_name, 1)
        top_layout.addWidget(self._clear_button, 0)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self._view)

        # connect
        self._view.selectionChanged.connect(self._on_value_changed)
        self._clear_button.clicked.connect(self._view.clearSelection)
        self.plate_name.currentTextChanged.connect(self._on_plate_name_changed)
        self._show_rotation.toggled.connect(self._on_show_rotation_toggled)

        if plan:
            self.setValue(plan)

    # _________________________PUBLIC METHODS_________________________ #

    def value(self) -> useq.WellPlatePlan:
        """Return the current plate and the selected wells as a `useq.WellPlatePlan`."""
        return useq.WellPlatePlan(
            plate=self._plate or useq.WellPlate.from_str(self.plate_name.currentText()),
            a1_center_xy=self._a1_center_xy,
            rotation=self._rotation,
            selected_wells=tuple(zip(*self.currentSelection())),
        )

    def setValue(self, value: useq.WellPlatePlan | useq.WellPlate | Mapping) -> None:
        """Set the current plate and the selected wells.

        Parameters
        ----------
        value : PlateInfo
            The plate information to set containing the plate and the selected wells
            as a list of (name, row, column).
        """
        if isinstance(value, useq.WellPlate):
            plan = useq.WellPlatePlan(plate=value, a1_center_xy=(0, 0))
        else:
            plan = useq.WellPlatePlan.model_validate(value)

        self._plate = plan.plate
        self._rotation = plan.rotation
        self._a1_center_xy = plan.a1_center_xy
        with signals_blocked(self):
            self.plate_name.setCurrentText(plan.plate.name)
        self._view.drawPlate(plan)

        if plan.rotation:
            self._show_rotation.show()
            self._show_rotation.setChecked(True)
        else:
            self._show_rotation.hide()
            self._show_rotation.setChecked(False)

    def currentSelection(self) -> tuple[tuple[int, int], ...]:
        """Return the indices of the selected wells as `((row, col), ...)`."""
        return self._view.selectedIndices()

    def setCurrentSelection(self, selection: IndexExpression) -> None:
        """Select the wells with the given indices.

        `selection` can be any 2-d numpy indexing expression, e.g.:
        - (0, 0)
        - [(0, 0), (1, 1), (2, 2)]
        - slice(0, 2)
        - (0, slice(0, 2))
        """
        self.setValue(
            useq.WellPlatePlan(
                plate=self.plate_name.currentText(),
                a1_center_xy=(0, 0),
                selected_wells=selection,
            )
        )

    # _________________________PRIVATE METHODS________________________ #

    def _on_value_changed(self) -> None:
        """Emit the valueChanged signal when the value changes."""
        self.valueChanged.emit(self.value())

    def _on_plate_name_changed(self, plate_name: str) -> None:
        plate = useq.WellPlate.from_str(plate_name)
        val = self.value().model_copy(update={"plate": plate, "selected_wells": None})
        self.setValue(val)

    def _on_show_rotation_toggled(self, checked: bool) -> None:
        rot = self._rotation if checked else None
        val = self.value().model_copy(update={"rotation": rot})
        self._view.drawPlate(val)
