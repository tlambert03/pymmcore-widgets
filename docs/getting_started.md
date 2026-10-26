# Getting Started

## Installation

### Installing pymmcore-widgets

You can install the latest release of [pymmcore-widgets](https://pypi.org/project/pymmcore-widgets/)
using uv/pip.  Note that you must manually select a Qt backend using an extra:

```sh
pip install pymmcore-widgets[PyQt6]
# or 
pip install pymmcore-widgets[PySide6]
```

!!! Note
    Widgets are tested on:

    * macOS & Windows
    * Python 3.10 and above
    * PyQt6 & PySide6 (we no longer test PyQt5/PySide2)

### Installing Micro-Manager

`pymmcore-widgets` depends on [pymmcore-plus](../pymmcore-plus/index.md), which is
installed automatically. You still need the Micro-Manager device adapters: see
[Installing Micro-Manager device adapters](../pymmcore-plus/install.md#installing-micro-manager-device-adapters).

## Usage

For a deeper understanding of each widget's functionality, browse the [widget gallery](widgets/index.md): each widget's page has a screenshot and a short example.

### Basic usage

As shown in the example from the [Overview](./index.md#usage) section, for a basic usage of any of the widgets we need to:

1. create a Qt Application.
2. create a Micro-Manager [core][pymmcore_plus.CMMCorePlus.instance] instance so that all the widgets will control the same core.
3. load a configuration file.
4. create and show the wanted widget(s).

In this example, we substitute step 3 with the [ConfigurationWidget][pymmcore_widgets.ConfigurationWidget] widget which enables us to load any `Micro-Manager` configuration file. Additionally, we use the [GroupPresetTableWidget][pymmcore_widgets.GroupPresetTableWidget] widget, which provides an interactive interface for the `groups` and `presets` stored in the configuration file.

```python title="basic_usage.py"
--8<-- "examples/basic_usage.py"
```

The code above will create a Qt Application with the `ConfigurationWidget` and `GroupPresetTableWidget`:

![type:video](./images/basic_usage.mp4){: style='width: 100%'}

!!! Note "Choosing a `Micro-Manager` core"
    Most widgets, by default, utilize the [global singleton core][pymmcore_plus.CMMCorePlus.instance] or instantiate a new one if none exists. Once instantiated, the global singleton core can be accessed using `CMMCorePlus.instance()`. This eliminates the need for manual core instance creation.

    For example, in the case above, the `ConfigurationWidget` is the first widget to be instantiated and it will automatically create a new core instance. This makes the `mmc = CMMCorePlus.instance()` line redundant and removable.
    
    However, if a specific core instance is required, you can create a core instance first and then pass it as the `mmcore` argument to the widget (if available, not all the widgets have it), like so: `GroupPresetTableWidget(mmcore=my_core)`.

You can add to this simple code any other widgets from this package to control and interact with the same [Micro-Manager core instance][pymmcore_plus.CMMCorePlus.instance].

### Custom GUI

Creating a custom GUI with the widgets from this package requires a deeper understanding of the Qt environment, such as [PyQt6](https://pypi.org/project/PyQt6/). However, this documentation does not primarily focus on this aspect.

As shown in the video below, in this section, we only provide a simple example to illustrate the process of building a custom GUI using some of the `pymmcore-widgets`.

![type:video](./images/my_widget.mp4){: style='width: 100%'}

Here we create a [Qt Application](https://doc.qt.io/qt-6/qapplication.html) with
a general-purpose [QWidget](https://doc.qt.io/qt-6/qwidget.html) that
incorporates a variety of `pymmcore-widgets`:
[ConfigurationWidget][pymmcore_widgets.ConfigurationWidget],
[ChannelGroupWidget][pymmcore_widgets.ChannelGroupWidget],
[ChannelWidget][pymmcore_widgets.ChannelWidget],
[DefaultCameraExposureWidget][pymmcore_widgets.DefaultCameraExposureWidget],
[ImagePreview][pymmcore_widgets.ImagePreview], [SnapButton][pymmcore_widgets.SnapButton],
and [LiveButton][pymmcore_widgets.LiveButton].

This simple GUI can be used to load a `Micro-Manager` configuration file, snap an image or live stream images from the camera, with the flexibility to select a channel and adjust the exposure time.

```python title="custom_gui.py"
--8<-- "examples/custom_gui.py"
```

For a ready-made application, see [pymmcore-gui](../pymmcore-gui/index.md) or [napari-micromanager](../napari-micromanager/index.md).
