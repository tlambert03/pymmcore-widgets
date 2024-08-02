import useq
from pymmcore_plus import CMMCorePlus
from qtpy.QtWidgets import QApplication

from pymmcore_widgets import StageWidget
from pymmcore_widgets.hcs._plate_navigator_widget import PlateNavigator

app = QApplication([])
mmc = CMMCorePlus.instance()
mmc.loadSystemConfiguration(r"C:\Users\Public\NIC\Micro-Manager\ti2.cfg")
plate = useq.WellPlatePlan(
    plate=useq.WellPlate.from_str("96-well"),
    a1_center_xy=(-54144, 33788),
    rotation=0,
)
wdg = PlateNavigator(mmcore=mmc)
wdg.set_plan(plate)
wdg.show()
stg = StageWidget("XYStage", mmcore=mmc)
stg._poll_cb.setChecked(True)
stg.show()
app.exec()
