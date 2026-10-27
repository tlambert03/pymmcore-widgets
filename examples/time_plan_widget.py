"""Example usage of the TimePlanWidget class.

TimePlanWidget edits a useq time plan.  It doesn't use a CMMCorePlus.

Check also the 'mda_widget.py' example to see the TimePlanWidget
used in combination of other widgets.
"""

import useq
from qtpy.QtWidgets import QApplication

from pymmcore_widgets import TimePlanWidget

app = QApplication([])

t_wdg = TimePlanWidget()
t_wdg.setValue(useq.TIntervalLoops(interval=3, loops=5))
t_wdg.valueChanged.connect(lambda: print(t_wdg.value()))
t_wdg.show()

app.exec()
