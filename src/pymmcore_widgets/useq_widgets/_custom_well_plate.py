import useq
from qtpy.QtCore import Signal
from qtpy.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QSpinBox,
    QWidget,
)
from superqt.utils import signals_blocked

from ._well_plate_view import WellPlateView


class CustomWellPlateWidget(QWidget):
    valueChanged = Signal(object)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self._catalog = QComboBox()
        self._catalog.addItems(("", *useq.registered_well_plate_keys()))
        self._catalog.currentTextChanged.connect(self._on_catalog_change)

        self.plate_name = QLineEdit()
        self.rows = QSpinBox()
        self.rows.setRange(1, 100)
        self.rows.setValue(8)
        self.columns = QSpinBox()
        self.columns.setRange(1, 100)
        self.columns.setValue(12)

        self.well_spacing_x = QDoubleSpinBox()
        self.well_spacing_x.setRange(0.1, 100)
        self.well_spacing_x.setValue(9)
        self.well_spacing_y = QDoubleSpinBox()
        self.well_spacing_y.setVisible(False)
        self.well_spacing_y.setRange(0.1, 100)
        self.well_spacing_y.setValue(9)

        self.well_width = QDoubleSpinBox()
        self.well_width.setRange(0.1, 100)
        self.well_width.setValue(6.4)
        self.well_height = QDoubleSpinBox()
        self.well_height.setVisible(False)
        self.well_height.setRange(0.1, 100)
        self.well_height.setValue(6.4)

        self.circular_wells = QCheckBox()
        self.circular_wells.setChecked(True)

        self._advanced = QCheckBox()

        self.form = form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.addRow("Plate Name", self.plate_name)
        form.addRow("Rows", self.rows)
        form.addRow("Columns", self.columns)
        form.addRow("Advanced", self._advanced)
        spacing = QHBoxLayout()
        spacing.addWidget(self.well_spacing_x)
        spacing.addWidget(self.well_spacing_y)
        form.addRow("Well Spacing (mm)", spacing)
        size = QHBoxLayout()
        size.addWidget(self.well_width)
        size.addWidget(self.well_height)
        form.addRow("Well Size (mm)", size)
        form.addRow("Circular Well", self.circular_wells)
        form.addRow("", self._catalog)

        self._view = WellPlateView(self)
        main_layout = QHBoxLayout(self)
        main_layout.addLayout(form, 1)
        main_layout.addWidget(self._view, 2)

        self.rows.valueChanged.connect(self._emit_new_value)
        self.columns.valueChanged.connect(self._emit_new_value)
        self.well_spacing_x.valueChanged.connect(self._emit_new_value)
        self.well_spacing_y.valueChanged.connect(self._emit_new_value)
        self.well_width.valueChanged.connect(self._emit_new_value)
        self.well_height.valueChanged.connect(self._emit_new_value)
        self.circular_wells.stateChanged.connect(self._emit_new_value)
        self.plate_name.textChanged.connect(self._emit_new_value)
        self._advanced.toggled.connect(self._on_show_height_toggled)

        self._view.drawPlate(self.value())
        self._view.setDragMode(self._view.DragMode.NoDrag)

    def value(self) -> useq.WellPlate:
        if self._advanced.isChecked():
            size = (self.well_width.value(), self.well_height.value())
            spacing = (self.well_spacing_x.value(), self.well_spacing_y.value())
        else:
            size = self.well_width.value()
            spacing = self.well_spacing_x.value()
        return useq.WellPlate(
            rows=self.rows.value(),
            columns=self.columns.value(),
            well_spacing=spacing,
            well_size=size,
            circular_wells=self.circular_wells.isChecked(),
            name=self.plate_name.text(),
        )

    def setValue(self, plate: useq.WellPlate) -> None:
        if plate == self.value():
            return
        with signals_blocked(self):
            self.rows.setValue(plate.rows)
            self.columns.setValue(plate.columns)
            self.well_spacing_x.setValue(plate.well_spacing[0])
            self.well_spacing_y.setValue(plate.well_spacing[1])
            self.well_width.setValue(plate.well_size[0])
            self.well_height.setValue(plate.well_size[1])
            self.circular_wells.setChecked(plate.circular_wells)
            self.plate_name.setText(plate.name)
        self.valueChanged.emit(plate)

    def _emit_new_value(self) -> None:
        val = self.value()
        self._view.drawPlate(val)
        self.valueChanged.emit(val)

    def _on_catalog_change(self, name: str) -> None:
        if name:
            self.setValue(useq.WellPlate.from_str(name))

    def _on_show_height_toggled(self, toggled: bool) -> None:
        self.well_height.setVisible(toggled)
        self.well_spacing_y.setVisible(toggled)
        self._emit_new_value()
