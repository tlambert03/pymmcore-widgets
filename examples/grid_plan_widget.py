"""Example usage of the GridPlanWidget class.

GridPlanWidget edits a useq grid plan.  It doesn't use a CMMCorePlus.

Check also the 'position_table.py' and 'mda_widget.py' examples to see the
GridPlanWidget used in combination of other widgets.
"""

from qtpy.QtWidgets import QApplication

from pymmcore_widgets import GridPlanWidget

app = QApplication([])

grid_wdg = GridPlanWidget()
grid_wdg.valueChanged.connect(print)
grid_wdg.show()

app.exec()
