# Building a Custom GUI

The widgets in `pymmcore-widgets` are ordinary `QWidget`s that control a
[`CMMCorePlus`][pymmcore_plus.CMMCorePlus], so you can arrange them with Qt layouts
like any other widget.  [Your first GUI](../getting-started/first-gui.md) puts a few of
them in a window.  This page covers the things you'll want to know once you start
building something bigger: which Qt to install, how widgets find their core, and a
larger example.

## Installing a Qt backend

`pymmcore-widgets` does *not* install Qt for you, so you choose the Qt backend with an
extra:

```sh
pip install "pymmcore-widgets[PyQt6]"
# or
pip install "pymmcore-widgets[PySide6]"
```

(Keep the quotes.  In zsh, the default shell on macOS, the square brackets otherwise
cause a "no matches found" error.)  You'll also need Python 3.11 or newer, and the
Micro-Manager device adapters (see [Installation](../getting-started/install.md)).

!!! question "PyQt6 or PySide6?"

    Qt is the C++ toolkit the widgets are drawn with, and PyQt6 and PySide6 are two
    sets of Python bindings for it.  The widgets work with (and are tested on) both,
    on macOS and Windows.  The main difference is the license.  PyQt6 is GPL (or
    commercial), and PySide6 is LGPL.  That matters if you distribute your GUI, for
    example as a bundled application.  If you don't have a reason to choose,
    PyQt6 is a fine default (it's what [pymmcore-gui](../pymmcore-gui/index.md) uses).

    We no longer test PyQt5 or PySide2 (and PySide2 can't be installed on Python
    3.11 or newer).

The widgets import Qt through [qtpy](https://github.com/spyder-ide/qtpy), which is
installed with `pymmcore-widgets`.  qtpy provides one API (`from qtpy.QtWidgets import
QApplication`) on top of whichever binding is installed, and the examples on this site
use it too.  If you write your own code against qtpy as well, it will run with either
backend.  (If both are installed in the same environment, qtpy picks PyQt6; set the
environment variable `QT_API=pyside6` to use PySide6.)

## Basic usage

For a basic use of any of the widgets, we need to:

1. create a Qt application (`QApplication`);
2. create a Micro-Manager [core][pymmcore_plus.CMMCorePlus.instance] instance so
   that all the widgets will control the same core;
3. load a configuration file;
4. create and show the widget(s) we want.

The order of the first two steps matters.  Create the `QApplication` before the core
(see [Qt integration](../pymmcore-plus/examples/integration-with-qt.md) for why).

In this example, we replace step 3 with the
[ConfigurationWidget][pymmcore_widgets.ConfigurationWidget], which lets us load any
Micro-Manager configuration file.  We also add the
[GroupPresetTableWidget][pymmcore_widgets.GroupPresetTableWidget], which shows the
configuration groups and presets stored in the configuration file:

```python title="basic_usage.py"
--8<-- "examples/basic_usage.py"
```

The code above will create a Qt application with the `ConfigurationWidget` and the
`GroupPresetTableWidget`:

![type:video](./images/basic_usage.mp4){: style='width: 100%'}

## Choosing a core

By default, most widgets use the [global singleton
core][pymmcore_plus.CMMCorePlus.instance], `CMMCorePlus.instance()`, and create it if
it doesn't exist yet.  This means that all the widgets in your GUI control the same
core without you connecting anything, and so does any other code that calls
`CMMCorePlus.instance()`.  (So in the example above, the `mmc = CMMCorePlus.instance()`
line isn't strictly necessary.  Without it, the `ConfigurationWidget` would create
the core.)

If you need a specific core instead, create it first and pass it to each widget as the
`mmcore` argument, for example `GroupPresetTableWidget(mmcore=my_core)`.  A few widgets
are different:

- The sequence editors ([`MDASequenceWidget`][pymmcore_widgets.MDASequenceWidget],
  [`ChannelTable`][pymmcore_widgets.ChannelTable],
  [`PositionTable`][pymmcore_widgets.PositionTable],
  [`TimePlanWidget`][pymmcore_widgets.TimePlanWidget],
  [`ZPlanWidget`][pymmcore_widgets.ZPlanWidget] and
  [`GridPlanWidget`][pymmcore_widgets.GridPlanWidget]) don't use a core at all.  They
  edit `useq` objects.  Read the result with `value()`, set it with `setValue()`, and
  connect to `valueChanged`.  [`MDAWidget`][pymmcore_widgets.MDAWidget] is the
  sequence editor that *is* connected to a core (and can run the acquisition).
- [`ConfigWizard`][pymmcore_widgets.ConfigWizard] calls the argument `core`, not
  `mmcore`.
- [`ConfigGroupsEditor`][pymmcore_widgets.ConfigGroupsEditor] and
  [`ConfigGroupsTree`][pymmcore_widgets.ConfigGroupsTree] are built from a core with
  `create_from_core(core)`, and don't follow it afterwards.
- [`InstallWidget`][pymmcore_widgets.InstallWidget] installs device adapters and
  doesn't need a core.

## Custom GUI

The widgets are ordinary `QWidget`s, so building a custom GUI with them is mostly a
matter of Qt layouts.  If you're new to Qt, the [Qt for Python
tutorials](https://doc.qt.io/qtforpython-6/tutorials/index.html) are a good place to
start.  Here, we only give a simple example of a custom GUI built from some of the
`pymmcore-widgets`.

We create a [Qt application](https://doc.qt.io/qt-6/qapplication.html) with
a general-purpose [QWidget](https://doc.qt.io/qt-6/qwidget.html) that
incorporates a variety of `pymmcore-widgets`:
[ConfigurationWidget][pymmcore_widgets.ConfigurationWidget],
[ChannelGroupWidget][pymmcore_widgets.ChannelGroupWidget],
[ChannelWidget][pymmcore_widgets.ChannelWidget],
[DefaultCameraExposureWidget][pymmcore_widgets.DefaultCameraExposureWidget],
[ImagePreview][pymmcore_widgets.ImagePreview], [SnapButton][pymmcore_widgets.SnapButton],
and [LiveButton][pymmcore_widgets.LiveButton].

This simple GUI can be used to load a Micro-Manager configuration file, snap an image
or stream images from the camera, with the flexibility to select a channel and adjust
the exposure time:

```python title="custom_gui.py"
--8<-- "examples/custom_gui.py"
```

Running it (and loading a configuration) looks like this:

![type:video](./images/my_widget.mp4){: style='width: 100%'}

## Next steps

The [widget gallery](widgets/index.md) lists the other widgets you can add, each with
an example.  If you'd rather start from a ready-made application, see
[pymmcore-gui](../pymmcore-gui/index.md) (which you can also extend with your own
widgets) or [napari-micromanager](../napari-micromanager/index.md).
