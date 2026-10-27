from pymmcore_plus import CMMCorePlus
from qtpy.QtWidgets import QApplication

from pymmcore_widgets import ConfigWizard

app = QApplication([])

mmc = CMMCorePlus.instance()
mmc.loadSystemConfiguration()

wiz = ConfigWizard()
wiz.show()

app.exec()
