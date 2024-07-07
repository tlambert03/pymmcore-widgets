from contextlib import suppress

with suppress(ImportError):
    pass

from qtpy.QtWidgets import QApplication
from useq import RelativePosition, WellPlate

from pymmcore_widgets.hcs._fov_widget import FOVSelectorWidget

app = QApplication([])

plate = WellPlate(rows=8, columns=12, well_spacing=(9, 9), well_size=(6.4, 6.4))
fs = FOVSelectorWidget(
    plate=plate, mode=RelativePosition(fov_width=512, fov_height=512)
)

fs.valueChanged.connect(print)

fs.show()

app.exec()
