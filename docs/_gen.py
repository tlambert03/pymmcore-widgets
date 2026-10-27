"""Generate docs content for pymmcore-widgets.  Run before building the docs.

For every widget listed in docs/widget_list.json this writes (all gitignored):

- docs/images/generated/<snake>.png       screenshot from examples/<snake>.py
- docs/images/generated/<snake>-dark.png  the same, in dark mode
- docs/api/pymmcore_widgets/<W>.md        widget page (screenshot, example, API)
- docs/_generated/<category>.md           gallery cards, for docs/widgets/index.md

All examples run in this process (with Qt's offscreen platform, unless
QT_QPA_PLATFORM says otherwise), sharing one QApplication.  Screenshots are only
regenerated when the example changed (or with --force).
"""

from __future__ import annotations

import argparse
import faulthandler
import gc
import json
import os
import re
import sys
import time
import traceback
import warnings
from pathlib import Path

import pymmcore_plus.core._mmcore_plus as mmcore_plus_module
from qtpy import QtWidgets
from qtpy.QtCore import QEvent, Qt
from qtpy.QtGui import QColor, QPalette
from qtpy.QtWidgets import QApplication, QWidget

import pymmcore_widgets

DOCS = Path(__file__).parent
ROOT = DOCS.parent
EXAMPLES = ROOT / "examples"
IMAGES = DOCS / "images" / "generated"
API = DOCS / "api" / "pymmcore_widgets"
OUT = DOCS / "_generated"
WIDGET_LIST = DOCS / "widget_list.json"
REPO = "https://github.com/pymmcore-plus/pymmcore-widgets"
# widgets whose example file doesn't follow the CamelCase -> snake_case rule
EXAMPLE_NAMES = {"StageExplorer": "stage_explorer_widget"}
# top-level widgets that are never the one to capture (popups)
SKIP = {"QFrame", "QMenu"}
TIMEOUT = 120  # seconds, per example

# The screenshot and the code that made it come first, then the API.
# - inherited_members: e.g. MDAWidget's valueChanged and time_plan come from
#   MDASequenceWidget, and ChannelTable's value/setValue from DataTableWidget
# - filters: Qt's event handlers and size hints aren't API anyone calls
PAGE = """\
---
title: {widget}
edit_url: {edit_url}
---

# {widget} {{#pymmcore_widgets.{widget}}}

{figure}
{example}
## API

::: pymmcore_widgets.{widget}
    options:
      show_root_heading: false
      heading_level: 3
      inherited_members: true
      filters:
        - "!^_"
        - "!^[a-z][a-zA-Z]*Event$"
        - "!^(eventFilter|sizeHint|minimumSizeHint)$"
"""

FIGURE = """\
<figure markdown>
  {images}
  <figcaption>
    Screenshot generated from the <a href="#example">example below</a>.
  </figcaption>
</figure>
"""

EXAMPLE = """\
## Example

```python title="examples/{snake}.py" linenums="1"
--8<-- "examples/{snake}.py"
```
"""


class _SharedApp(QApplication):
    """What examples get as `QApplication`: the app that is already running."""

    def __new__(cls, *args: object, **kwargs: object) -> QApplication:
        return QApplication.instance()


def _snake(name: str) -> str:
    if name in EXAMPLE_NAMES:
        return EXAMPLE_NAMES[name]
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _image(widget: str, dark: bool) -> Path:
    return IMAGES / f"{_snake(widget)}{'-dark' if dark else ''}.png"


def _settle(app: QApplication) -> None:
    for _ in range(5):
        app.processEvents()


def _set_scheme(app: QApplication, dark: bool) -> None:
    """Switch the app to light or dark mode."""
    scheme = Qt.ColorScheme.Dark if dark else Qt.ColorScheme.Light
    app.styleHints().setColorScheme(scheme)
    if app.styleHints().colorScheme() != scheme:
        # the platform can't switch (e.g. offscreen): use a dark palette instead
        palette = QPalette(QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
        for role in ("WindowText", "Text", "ButtonText", "PlaceholderText"):
            role = getattr(QPalette.ColorRole, role)
            palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(120, 120, 120))
        app.setPalette(palette if dark else app.style().standardPalette())
    _settle(app)


def start_app() -> QApplication:
    """Create the QApplication that every example will share."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")  # no windows popping up
    faulthandler.enable()  # if an example crashes the process, show where
    app = QApplication([])
    QApplication.exec = QApplication.exec_ = lambda *_: 0  # type: ignore
    QtWidgets.QApplication = _SharedApp
    return app


def screenshot(app: QApplication, widget: str, example: Path, dark: bool) -> str | None:
    """Run `example` in light or dark mode, save a grab of `widget`, and clean up.

    Returns a description of the problem, if any.
    """
    before = set(app.topLevelWidgets())
    # each example gets its own global core (the first CMMCorePlus it creates)
    mmcore_plus_module._instance = None
    # set before the example runs: some widgets pick their colors when created
    _set_scheme(app, dark)
    ns = {"__name__": "__main__", "__file__": str(example)}
    faulthandler.dump_traceback_later(TIMEOUT, exit=True)
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            code = compile(example.read_text(encoding="utf-8"), str(example), "exec")
            exec(code, ns)
            _settle(app)
        # superqt draws a "?" for icons it can't fetch from the Iconify API
        if failed := [
            str(w.message) for w in caught if "fetching icon" in str(w.message)
        ]:
            return f"{len(failed)} icon(s) not fetched: {failed[0]}"
        shown = [
            w
            for w in app.topLevelWidgets()
            if w not in before and w.isVisible() and type(w).__name__ not in SKIP
        ]
        if not shown:
            return f"{example.name} showed no widget"
        target = next((w for w in shown if type(w).__name__ == widget), shown[0])
        target.setMinimumWidth(300)  # turns out this is very important for grab
        target.activateWindow()  # as if it were the only window (active styling)
        _settle(app)
        IMAGES.mkdir(parents=True, exist_ok=True)
        target.grab().save(str(_image(widget, dark)))
    except Exception:
        return f"screenshot failed\n{traceback.format_exc(limit=-3)}"
    finally:
        faulthandler.cancel_dump_traceback_later()
        for w in app.topLevelWidgets():
            # popups are windows too, but get deleted with their parent widget
            if w not in before and w.parent() is None:
                w.close()
                w.deleteLater()
        ns.clear()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        gc.collect()
    return None


def _image_md(widget: str, prefix: str, attrs: str) -> str:
    """Markdown for the screenshot, switching with the site's light/dark theme."""
    light, dark = _image(widget, dark=False), _image(widget, dark=True)
    if not light.exists():
        return ""
    if not dark.exists():
        return f"![{widget}]({prefix}{light.name}){{ {attrs} }}"
    return (
        f"![{widget}]({prefix}{light.name}#only-light){{ {attrs} }}"
        f"![{widget}]({prefix}{dark.name}#only-dark){{ {attrs} }}"
    )


def _summary(widget: str) -> str:
    doc = (getattr(pymmcore_widgets, widget).__doc__ or "").strip()
    return " ".join(doc.split("\n\n")[0].split())


def write_pages(categories: dict[str, list[str]]) -> None:
    API.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(exist_ok=True)
    for category, widgets in categories.items():
        cards = ['<div class="grid cards pymm-gallery" markdown>', ""]
        for widget in widgets:
            snake = _snake(widget)
            has_example = (EXAMPLES / f"{snake}.py").exists()
            edit_url = (
                f"{REPO}/edit/main/examples/{snake}.py"
                if has_example
                else f"{REPO}/tree/main/src/pymmcore_widgets"
            )
            figure = _image_md(
                widget, "../../images/generated/", "loading=lazy .widget-image"
            )
            page = PAGE.format(
                widget=widget,
                edit_url=edit_url,
                figure=FIGURE.format(images=figure) if figure else "",
                example=EXAMPLE.format(snake=snake) if has_example else "",
            )
            (API / f"{widget}.md").write_text(page, encoding="utf-8")
            img = _image_md(widget, "../images/generated/", "loading=lazy")
            if img:
                img = f"[{img}](../api/pymmcore_widgets/{widget}.md)\n\n    "
            cards += [
                f"-   {img}[**`{widget}`**](../api/pymmcore_widgets/{widget}.md)",
                "",
                f"    {_summary(widget)}",
                "",
            ]
        cards.append("</div>")
        (OUT / f"{category}.md").write_text("\n".join(cards) + "\n", encoding="utf-8")


def check_coverage(categories: dict[str, list[str]]) -> list[str]:
    listed = {w for ws in categories.values() for w in ws}
    exported = set()
    for name in pymmcore_widgets.__all__:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            obj = getattr(pymmcore_widgets, name)
        deprecated = any(issubclass(w.category, DeprecationWarning) for w in caught)
        if isinstance(obj, type) and issubclass(obj, QWidget) and not deprecated:
            exported.add(name)
    return [
        f"{w}: exported but missing from widget_list.json"
        for w in sorted(exported - listed)
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force", action="store_true", help="regenerate all screenshots"
    )
    ns = parser.parse_args()

    categories: dict[str, list[str]] = json.loads(
        WIDGET_LIST.read_text(encoding="utf-8")
    )
    widgets = [w for ws in categories.values() for w in ws]
    problems: list[str] = []
    shots: dict[tuple[str, bool], Path] = {}  # (widget, dark) -> example
    for widget in widgets:
        example = EXAMPLES / f"{_snake(widget)}.py"
        if not example.exists():
            problems.append(f"{widget}: no example at {example.relative_to(ROOT)}")
            continue
        mtime = example.stat().st_mtime
        for dark in (False, True):
            img = _image(widget, dark)
            if ns.force or not img.exists() or img.stat().st_mtime < mtime:
                shots[(widget, dark)] = example

    if shots:
        app = start_app()
        results = {(w, d): screenshot(app, w, ex, d) for (w, d), ex in shots.items()}
        # Retry failures, after a pause: some widgets fetch icons from the Iconify
        # API (via pyconify), which may refuse requests for a while (rate limits).
        for delay in (15, 45):
            if not (failed := [shot for shot, problem in results.items() if problem]):
                break
            time.sleep(delay)
            results.update(
                {(w, d): screenshot(app, w, shots[w, d], d) for w, d in failed}
            )
        problems += [
            f"{widget}{' (dark)' if dark else ''}: {problem}"
            for (widget, dark), problem in results.items()
            if problem
        ]

    write_pages(categories)
    problems += check_coverage(categories)
    for p in problems:
        print(f"[pymmcore-widgets] WARNING: {p}", file=sys.stderr)
    print(f"[pymmcore-widgets] {len(widgets)} widget pages")


if __name__ == "__main__":
    main()
