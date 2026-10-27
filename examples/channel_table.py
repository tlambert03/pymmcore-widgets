"""Example usage of the ChannelTable class.

ChannelTable edits a list of `useq.Channel`s.  It doesn't use a CMMCorePlus, so
you tell it which channel groups and channels to offer.

Check also the 'mda_widget.py' example to see the ChannelTable
used in combination of other widgets.
"""

from qtpy.QtWidgets import QApplication

from pymmcore_widgets import ChannelTable

app = QApplication([])

ch_table_wdg = ChannelTable(rows=1)
ch_table_wdg.setChannelGroups({"Channel": ["DAPI", "FITC"]})
ch_table_wdg.valueChanged.connect(lambda: print(ch_table_wdg.value()))
ch_table_wdg.resize(500, 200)
ch_table_wdg.show()

app.exec()
