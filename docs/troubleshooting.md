# Troubleshooting Qt and Widgets

For problems with the core itself (finding Micro-Manager, loading device adapters),
see [Troubleshooting](../pymmcore-plus/troubleshooting.md) for pymmcore-plus.

## No Qt bindings

```sh
qtpy.QtBindingsNotFoundError: No Qt bindings could be found
```

If you get an error similar to the one above, it means that you did not install one
of the necessary [PyQt](https://riverbankcomputing.com/software/pyqt/) or
[PySide](https://www.qt.io/qt-for-python) libraries.  Install `pymmcore-widgets` with
an extra that brings one along:

```sh
pip install "pymmcore-widgets[PyQt6]"  # or "pymmcore-widgets[PySide6]"
```

See [Installing a Qt backend](getting_started.md#installing-a-qt-backend) for how to
choose.

## "no matches found" when installing

```sh
zsh: no matches found: pymmcore-widgets[PyQt6]
```

zsh (the default shell on macOS) treats the square brackets as a file pattern.  Put
quotes around the package name: `pip install "pymmcore-widgets[PyQt6]"`.

## Must construct a QApplication

```text
QWidget: Must construct a QApplication before a QWidget
```

... followed by Python crashing.  Every Qt program needs a `QApplication`, and it must
exist before you create any widget.  Create it first thing (and create it *before* the
`CMMCorePlus`, too, for the reasons explained in [Qt
integration](../pymmcore-plus/examples/integration-with-qt.md#create-the-qapplication-first)):

```python
from qtpy.QtWidgets import QApplication

app = QApplication([])
# ... now create the core and the widgets
app.exec()
```

## The widgets don't follow my script

If you change something from your own code (`core.setExposure(50)`, say) and a widget
doesn't update, the widget is probably connected to a different core.  Widgets use the
global `CMMCorePlus.instance()` unless you pass `mmcore=`, so a core you created with
`CMMCorePlus()` is a separate object, with its own devices and its own events.  Either
use `CMMCorePlus.instance()` in your script, or pass your core to each widget:
`ExposureWidget(mmcore=my_core)`.

Also check that the widget uses a core at all (the sequence editors, like
`ChannelTable` and `ZPlanWidget`, don't).  See [Choosing a
core](getting_started.md#choosing-a-core).

## The GUI freezes

Anything that blocks the main thread (the one running `app.exec()`) freezes the whole
GUI until it returns: a long `core.snapImage()`, a slow stage move, a `time.sleep()`
in a callback, etc...  Run long operations in a thread instead.
[`CMMCorePlus.run_mda`][pymmcore_plus.CMMCorePlus.run_mda] already does this for you.
See [Qt integration](../pymmcore-plus/examples/integration-with-qt.md) for an example.

Please [open an issue](https://github.com/pymmcore-plus/pymmcore-widgets/issues) if
you run into something that isn't covered here.
