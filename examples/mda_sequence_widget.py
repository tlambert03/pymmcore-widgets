"""MDASequenceWidget is a widget for creating a useq.MDASequence object.

It has no awareness of the CMMCorePlus object, and does not have a "run" button.
"""

import useq
from qtpy.QtWidgets import QApplication

from pymmcore_widgets import MDASequenceWidget

app = QApplication([])

wdg = MDASequenceWidget()
# without a core, the widget doesn't know your channels: tell it what to offer
wdg.channels.setChannelGroups({"Channel": ["DAPI", "FITC"]})
wdg.setValue(
    useq.MDASequence(
        channels=["DAPI", "FITC"],
        time_plan=useq.TIntervalLoops(interval=0.5, loops=11),
    )
)
wdg.valueChanged.connect(lambda: print(wdg.value()))
wdg.show()
app.exec()
