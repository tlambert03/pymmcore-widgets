"""Generate docs content for pymmcore-widgets.  Run before building the docs.

For every widget listed in docs/widget_list.json this writes (all gitignored):

- docs/images/generated/<snake>.png   screenshot from examples/<snake>.py
- docs/api/pymmcore_widgets/<W>.md    the widget's API page (screenshot, API, example)
- docs/_generated/<category>.md       gallery cards, included by docs/widgets/index.md

Screenshots run each example in a subprocess with Qt's offscreen platform, and are
only regenerated when the example changed (or with --force).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

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

PAGE = """\
---
title: {widget}
edit_url: {edit_url}
---

# {widget} {{#pymmcore_widgets.{widget}}}

{figure}
::: pymmcore_widgets.{widget}
    options:
      show_root_heading: false
      heading_level: 2

{example}
"""

FIGURE = """\
<figure markdown>
  ![{widget}](../../images/generated/{snake}.png){{ loading=lazy, .widget-image }}
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


def _snake(name: str) -> str:
    if name in EXAMPLE_NAMES:
        return EXAMPLE_NAMES[name]
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def screenshot(widget: str, example: Path, dest: Path) -> None:
    """Run `example` (in this process) and save a grab of `widget`."""
    from qtpy.QtWidgets import QApplication

    QApplication.exec = QApplication.exec_ = lambda *_: 0  # type: ignore
    ns = {"__name__": "__main__", "__file__": str(example)}
    exec(compile(example.read_text(encoding="utf-8"), str(example), "exec"), ns)
    app = QApplication.instance()
    for _ in range(5):
        app.processEvents()
    skip = {"QFrame", "QMenu"}
    tops = [
        w
        for w in app.topLevelWidgets()
        if w.isVisible() and type(w).__name__ not in skip
    ]
    if not tops:
        raise RuntimeError(f"{example.name} showed no widget")
    target = next((w for w in tops if type(w).__name__ == widget), tops[0])
    target.setMinimumWidth(300)  # turns out this is very important for grab
    app.processEvents()
    dest.parent.mkdir(parents=True, exist_ok=True)
    target.grab().save(str(dest))


def _shoot(widget: str, force: bool) -> str | None:
    example = EXAMPLES / f"{_snake(widget)}.py"
    dest = IMAGES / f"{_snake(widget)}.png"
    if not example.exists():
        return f"{widget}: no example at {example.relative_to(ROOT)}"
    if dest.exists() and not force and dest.stat().st_mtime > example.stat().st_mtime:
        return None
    # offscreen by default (no windows popping up); CI may choose a native platform
    env = {"QT_QPA_PLATFORM": "offscreen", **os.environ, "PYMM_LOG_FILE": "0"}
    try:
        subprocess.run(
            [sys.executable, __file__, "--shoot", widget, str(example), str(dest)],
            env=env,
            check=True,
            timeout=120,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        return f"{widget}: screenshot failed\n{e.stderr[-1500:]}"
    except subprocess.TimeoutExpired:
        return f"{widget}: screenshot timed out"
    return None


def _summary(widget: str) -> str:
    import pymmcore_widgets

    doc = (getattr(pymmcore_widgets, widget).__doc__ or "").strip()
    return " ".join(doc.split("\n\n")[0].split())


def write_pages(categories: dict[str, list[str]]) -> None:
    API.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(exist_ok=True)
    for category, widgets in categories.items():
        cards = ['<div class="grid cards pymm-gallery" markdown>', ""]
        for widget in widgets:
            snake = _snake(widget)
            has_img = (IMAGES / f"{snake}.png").exists()
            has_example = (EXAMPLES / f"{snake}.py").exists()
            edit_url = (
                f"{REPO}/edit/main/examples/{snake}.py"
                if has_example
                else f"{REPO}/tree/main/src/pymmcore_widgets"
            )
            page = PAGE.format(
                widget=widget,
                edit_url=edit_url,
                figure=FIGURE.format(widget=widget, snake=snake) if has_img else "",
                example=EXAMPLE.format(snake=snake) if has_example else "",
            )
            (API / f"{widget}.md").write_text(page, encoding="utf-8")
            img = (
                f"[![{widget}](../images/generated/{snake}.png){{ loading=lazy }}]"
                f"(../api/pymmcore_widgets/{widget}.md)\n\n    "
                if has_img
                else ""
            )
            cards += [
                f"-   {img}[**`{widget}`**](../api/pymmcore_widgets/{widget}.md)",
                "",
                f"    {_summary(widget)}",
                "",
            ]
        cards.append("</div>")
        (OUT / f"{category}.md").write_text("\n".join(cards) + "\n", encoding="utf-8")


def check_coverage(categories: dict[str, list[str]]) -> list[str]:
    import warnings

    from qtpy.QtWidgets import QWidget

    import pymmcore_widgets

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
    parser.add_argument("--shoot", nargs=3, metavar=("WIDGET", "EXAMPLE", "DEST"))
    ns = parser.parse_args()
    if ns.shoot:
        widget, example, dest = ns.shoot
        return screenshot(widget, Path(example), Path(dest))

    categories: dict[str, list[str]] = json.loads(
        WIDGET_LIST.read_text(encoding="utf-8")
    )
    widgets = [w for ws in categories.values() for w in ws]
    with ThreadPoolExecutor(max_workers=min(8, os.cpu_count() or 2)) as pool:
        problems = [p for p in pool.map(lambda w: _shoot(w, ns.force), widgets) if p]
    write_pages(categories)
    problems += check_coverage(categories)
    for p in problems:
        print(f"[pymmcore-widgets] WARNING: {p}", file=sys.stderr)
    print(f"[pymmcore-widgets] {len(widgets)} widget pages")


if __name__ == "__main__":
    main()
