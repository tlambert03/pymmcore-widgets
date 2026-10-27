"""Example usage of the PositionTable class.

PositionTable edits a list of `useq.Position`s.  It doesn't use a CMMCorePlus
(the table inside MDAWidget does, so that it can add the current stage position).

Check also the 'mda_widget.py' example to see the PositionTable
used in combination of other widgets.
"""

from qtpy.QtWidgets import QApplication

from pymmcore_widgets import PositionTable

app = QApplication([])

pos_wdg = PositionTable(rows=3)
pos_wdg.valueChanged.connect(lambda: print(pos_wdg.value()))
pos_wdg.resize(570, 200)
pos_wdg.show()

app.exec()
