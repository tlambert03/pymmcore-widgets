# pymmcore-widgets

[pymmcore-widgets](https://github.com/pymmcore-plus/pymmcore-widgets) is a library of
Qt widgets for [pymmcore-plus](../pymmcore-plus/index.md), meant for building your own
microscope GUI in Python.  There are widgets for most of the things you do at the
microscope (channels, exposure, stages, device properties, configuration groups,
snapping and live mode, multi-dimensional acquisitions) and for setting it up (the
Hardware Configuration Wizard, pixel sizes, installing device adapters).  Most of them
control a [`CMMCorePlus`][pymmcore_plus.CMMCorePlus] and follow its
[events](../pymmcore-plus/guides/events.md), so they stay in sync with each other and
with your own code.  They are also the building blocks of
[pymmcore-gui](../pymmcore-gui/index.md) and
[napari-micromanager](../napari-micromanager/index.md).

<figure markdown>
![Several pymmcore-widgets in one window](images/generated/stage_explorer_widget.png#only-light){ loading=lazy }
![Several pymmcore-widgets in one window](images/generated/stage_explorer_widget-dark.png#only-dark){ loading=lazy }
<figcaption markdown>
A few widgets in one window (the code is the
[StageExplorer example](api/pymmcore_widgets/StageExplorer.md#example)).
</figcaption>
</figure>

## Where to start

- [Your first GUI](../getting-started/first-gui.md) puts a few of them together in a
  window.
- The [widget gallery](widgets/index.md) shows each widget with a screenshot, and links
  to its page with a runnable example and the API.
- [Building a custom GUI](getting_started.md) covers choosing a Qt backend, how
  widgets find their core, and a larger example.
- [Qt integration](../pymmcore-plus/examples/integration-with-qt.md) explains how
  pymmcore-plus and Qt work together (and how to keep your GUI responsive).

## API reference

Import widgets from the top-level package:

```python
from pymmcore_widgets import MDAWidget, PropertyBrowser, StageWidget
```

Each of these has its own page (listed under `pymmcore_widgets` in the
sidebar, and in the [gallery](widgets/index.md)).  A few more specialized widgets live
in submodules: the sequence editors' building blocks in
[`pymmcore_widgets.useq_widgets`](api/pymmcore_widgets/useq_widgets/index.md) (for
example [`WellPlateWidget`][pymmcore_widgets.useq_widgets.WellPlateWidget] and
[`PointsPlanWidget`][pymmcore_widgets.useq_widgets.PointsPlanWidget]), and
[`StackViewer`][pymmcore_widgets.experimental.StackViewer] in
`pymmcore_widgets.experimental`.
