"""MDAWidget is a widget for creating and running a useq.MDASequence.

It is fully connected to the CMMCorePlus object, and has a "run" button.
"""

from contextlib import suppress

import useq
from pymmcore_plus import CMMCorePlus
from qtpy.QtWidgets import QApplication

from pymmcore_widgets import MDAWidget

with suppress(ImportError):
    from rich import print

app = QApplication([])

CMMCorePlus.instance().loadSystemConfiguration()

wdg = MDAWidget()
# start from a sequence (or build one in the GUI)
wdg.setValue(
    useq.MDASequence(
        channels=["DAPI", "FITC"],
        time_plan=useq.TIntervalLoops(interval=0.5, loops=11),
    )
)
wdg.valueChanged.connect(lambda: print(wdg.value()))
wdg.show()
app.exec()
