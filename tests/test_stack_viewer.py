from pymmcore_plus import CMMCorePlus
from superqt.cmap._cmap_utils import try_cast_colormap
from useq import MDASequence
from vispy.app.canvas import MouseEvent
from vispy.scene.events import SceneMouseEvent

from pymmcore_widgets._mda._stack_viewer import StackViewer
from pymmcore_widgets._mda._util._channel_row import CMAPS

sequence = MDASequence(
    channels=[{"config": "DAPI", "exposure": 10}, {"config": "FITC", "exposure": 10}],
    time_plan={"interval": 0.5, "loops": 3},
    axis_order="tpcz",
)


def test_acquisition(qtbot):
    mmcore = CMMCorePlus.instance()
    canvas = StackViewer(mmcore=mmcore)
    qtbot.addWidget(canvas)

    with qtbot.waitSignal(mmcore.mda.events.sequenceFinished):
        mmcore.mda.run(sequence)
    assert canvas.images[0][0]._data.flatten()[0] != 0
    assert canvas.images[1][0]._data.shape == (512, 512)
    assert len(canvas.channel_row.boxes) == 5
    assert len(canvas.sliders) > 1


def test_init_with_sequence(qtbot):
    mmcore = CMMCorePlus.instance()

    canvas = StackViewer(sequence=sequence, mmcore=mmcore)
    qtbot.addWidget(canvas)

    with qtbot.waitSignal(mmcore.mda.events.sequenceFinished):
        mmcore.mda.run(sequence)
    assert canvas.images[0][0]._data.flatten()[0] != 0
    assert canvas.images[1][0]._data.shape == (512, 512)
    # Now only the necessary sliders/boxes should have been initialized
    assert len(canvas.channel_row.boxes) == 2
    assert len(canvas.sliders) == 1


def test_interaction(qtbot):
    mmcore = CMMCorePlus.instance()
    canvas = StackViewer(mmcore=mmcore)
    qtbot.addWidget(canvas)

    with qtbot.waitSignal(mmcore.mda.events.sequenceFinished):
        mmcore.mda.run(sequence)

    event = SceneMouseEvent(MouseEvent("mouse_move"), None)
    event._pos = [100, 100, 0, 0]
    canvas.on_mouse_move(event)
    assert canvas.info_bar.text() != ""

    # outside canvas
    event._pos = [-10, 100, 0, 0]
    canvas.on_mouse_move(event)
    assert canvas.info_bar.text() != ""

    # outside image
    event._pos = [1000, 100, 0, 0]
    canvas.on_mouse_move(event)
    assert canvas.info_bar.text() != ""

    canvas.sliders[0].setValue(1)
    canvas.on_clim_timer()
    color_selected = 2
    canvas.channel_row.boxes[0].color_choice.setCurrentIndex(color_selected)
    assert (
        canvas.images[0][0].cmap.colors[-1].RGB
        == try_cast_colormap(CMAPS[color_selected]).to_vispy().colors[-1].RGB
    ).all

    canvas.channel_row.boxes[0].autoscale_chbx.setChecked(False)
    canvas.channel_row.boxes[0].slider.setValue((0, 255))
    canvas.channel_row.boxes[0].show_channel.setChecked(False)


def test_sequence_no_channels(qtbot):
    mmcore = CMMCorePlus.instance()
    canvas = StackViewer(mmcore=mmcore)
    qtbot.addWidget(canvas)
    sequence = MDASequence(time_plan={"interval": 0.5, "loops": 3})
    with qtbot.waitSignal(mmcore.mda.events.sequenceFinished):
        mmcore.mda.run(sequence)