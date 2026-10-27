# Widget Gallery

The top-level widgets in `pymmcore-widgets`, grouped by what they do, roughly in the
order you'd reach for them when building a GUI.  Click a widget for a runnable example
and its API (the screenshots are generated from those examples).

Most of these widgets control a [`CMMCorePlus`][pymmcore_plus.CMMCorePlus] (by
default the global [`CMMCorePlus.instance()`][pymmcore_plus.CMMCorePlus.instance], or
the one you pass as `mmcore=`).  They follow the core's
[events](../../pymmcore-plus/guides/events.md), so they stay in sync with each other
and with your own code.  The [sequence editors](#sequence-editors) are the exception:
they don't use a core at all.  (See [Building a custom
GUI](../getting_started.md#choosing-a-core) for the details.)

## Camera and images

Snap and live buttons, an image preview, and the camera's exposure and ROI.

--8<-- "docs/_generated/camera_widgets.md"

## Channels, objectives and presets

These widgets show (and change) the current state of the microscope: the channel, the
objective, the preset of any configuration group, and the shutters.

--8<-- "docs/_generated/state_widgets.md"

## Stages

Move an XY or Z stage, or explore the sample in a zoomable view of the stage, where
snapped images appear at the position they were taken.

--8<-- "docs/_generated/stage_widgets.md"

## Devices and properties

View and change the properties of any of the loaded devices.

--8<-- "docs/_generated/device_property_widgets.md"

## Acquisition

Define a multi-dimensional acquisition (a [`useq.MDASequence`][]) and run it on the
core.  [`MDAWidget`][pymmcore_widgets.MDAWidget] is the
[`MDASequenceWidget`][pymmcore_widgets.MDASequenceWidget] below, connected to a core.
It offers the core's channels, can add the current stage position, and has buttons to
run, pause and cancel the acquisition.

--8<-- "docs/_generated/mda_widgets.md"

## Sequence editors

!!! note "No core needed"

    These widgets edit `useq` objects and don't touch the microscope.  Read the
    result with `value()`, set it with `setValue()`, and connect to `valueChanged`
    to hear about changes.  Use them to describe an experiment in your own GUI; to
    run one, pass the sequence to
    [`CMMCorePlus.run_mda`][pymmcore_plus.CMMCorePlus.run_mda] (or use the
    [`MDAWidget`][pymmcore_widgets.MDAWidget] above).

--8<-- "docs/_generated/sequence_widgets.md"

## Configuration and setup

Load, create and edit a configuration file (the
[`ConfigWizard`][pymmcore_widgets.ConfigWizard] is Micro-Manager's Hardware
Configuration Wizard), set pixel sizes, install device adapters, and watch the core's
log.

--8<-- "docs/_generated/configuration_widgets.md"
