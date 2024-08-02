import useq
from pymmcore_plus import CMMCorePlus
from qtpy.QtWidgets import QApplication, QWidget, QHBoxLayout

from pymmcore_widgets import StageWidget
from pymmcore_widgets.hcs._plate_navigator_widget import PlateNavigator
from pymmcore_widgets.hcs._plate_calibration_widget import PlateCalibrationWidget

app = QApplication([])
mmc = CMMCorePlus.instance()
mmc.loadSystemConfiguration(r"C:\Users\Public\NIC\Micro-Manager\ti2.cfg")
plate = useq.WellPlatePlan(
    plate=useq.WellPlate.from_str("12-well"),
    a1_center_xy=(0, 0),
    rotation=0,
)
print(plate)


wdgCal = PlateCalibrationWidget(mmcore=mmc)
wdgCal.setPlate(plate)

wdg = PlateNavigator(mmcore=mmc)
wdg.set_plan(plate)

@wdgCal.calibrationChanged.connect
def _on_calibration_changed(calibrated: bool):
    if calibrated:
        wdg.set_plan(wdgCal.platePlan())
        print("Calibrated")

stg = StageWidget("XYStage", mmcore=mmc)
stg._poll_cb.setChecked(True)

main = QWidget()
layout = QHBoxLayout()
layout.addWidget(wdg)
layout.addWidget(wdgCal)
layout.addWidget(stg)
main.setLayout(layout)
main.show()
app.exec()
