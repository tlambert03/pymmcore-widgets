"""Example usage of the ZPlanWidget class.

ZPlanWidget edits a useq z plan.  It doesn't use a CMMCorePlus.

Check also the 'mda_widget.py' example to see the ZPlanWidget
used in combination of other widgets.
"""

from qtpy.QtWidgets import QApplication

from pymmcore_widgets import ZPlanWidget

app = QApplication([])

z_wdg = ZPlanWidget()
z_wdg.valueChanged.connect(print)
z_wdg.show()

app.exec()
