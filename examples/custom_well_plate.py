from contextlib import suppress

from qtpy.QtWidgets import QApplication

from pymmcore_widgets.useq_widgets._custom_well_plate import CustomWellPlateWidget

with suppress(ImportError):
    from rich import print


app = QApplication([])

wdg = CustomWellPlateWidget()
wdg.valueChanged.connect(print)
wdg.show()

app.exec()
