"""Generate widget pages and tables. Run before `zensical build`."""

from __future__ import annotations

import json
import re
from pathlib import Path
from textwrap import dedent

DOCS = Path(__file__).parent
GENERATED = DOCS.parent / "_generated"
WIDGET_LIST = DOCS / "widget_list.json"
WIDGETS = DOCS / "widgets"
EXAMPLES = DOCS.parent / "examples"
IMAGES = DOCS / "images"

TEMPLATE = """\
<figure markdown>
  ![{widget} widget](../images/{snake}.png){{ loading=lazy, class="widget-image" }}
  <figcaption>
    This image generated from <a href="#example">example code below</a>.
  </figcaption>
</figure>

::: pymmcore_widgets.{widget}

## Example

```python linenums="1" title="{snake}.py"
--8<-- "examples/{snake}.py"
```
"""


def _camel_to_snake(name: str) -> str:
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def generate_widget_tables() -> None:
    """Generate markdown snippet files for each widget section table."""
    from qtpy.QtWidgets import QWidget

    import pymmcore_widgets

    with open(WIDGET_LIST) as f:
        widget_dict = json.load(f)

    GENERATED.mkdir(exist_ok=True)

    for section, widget_list in widget_dict.items():
        table = ["| Widget | Description |", "| ------ | ----------- |"]
        for name in dir(pymmcore_widgets):
            if name.startswith("_") or name not in widget_list:
                continue
            obj = getattr(pymmcore_widgets, name)
            if isinstance(obj, type) and issubclass(obj, QWidget):
                doc = (obj.__doc__ or "").strip().splitlines()[0]
                table.append(f"| [{name}]({name}.md) | {doc} |")

        (GENERATED / f"{section}_widgets.md").write_text("\n".join(table))
        print(f"  Generated {section}_widgets.md")


def generate_widget_pages() -> None:
    """Generate per-widget doc pages with screenshots."""
    from pymmcore_plus.core import _mmcore_plus
    from qtpy.QtWidgets import QApplication

    with open(WIDGET_LIST) as f:
        widget_dict = json.load(f)

    WIDGETS.mkdir(exist_ok=True)
    IMAGES.mkdir(exist_ok=True)

    seen: set[int] = set()

    for _, widgets in widget_dict.items():
        for widget in widgets:
            # skip widgets that have manually-written pages
            if (WIDGETS / f"{widget}.md").exists():
                continue

            snake = _camel_to_snake(widget)
            example_path = EXAMPLES / f"{snake}.py"
            if not example_path.exists():
                print(f"  SKIP {widget}: no example at {example_path}")
                continue

            # Generate the markdown page
            md = dedent(TEMPLATE.format(widget=widget, snake=snake))
            (WIDGETS / f"{widget}.md").write_text(md)

            # Generate the screenshot
            img_path = str(IMAGES / f"{snake}.png")
            try:
                src = example_path.read_text().strip()
                src = src.replace(
                    "QApplication([])",
                    "QApplication.instance() or QApplication([])",
                )
                src = src.replace("app.exec_()", "")
                src = src.replace("app.exec()", "")
                gl = {**globals().copy(), "__name__": "__main__"}
                exec(src, gl, gl)

                app = QApplication.instance() or QApplication([])
                new = [w for w in app.topLevelWidgets() if id(w) not in seen]
                new = [
                    w
                    for w in new
                    if w.__class__.__name__ not in ["QFrame", "QMenu"]
                ]
                seen.update(id(w) for w in new)

                if new:
                    w = next(
                        (w for w in new if w.__class__.__name__ == widget),
                        new[0],
                    )
                    w.setMinimumWidth(300)
                    w.grab().save(img_path)

                # clean up core instance
                del _mmcore_plus._instance
                _mmcore_plus._instance = None
                for w in app.topLevelWidgets():
                    w.deleteLater()
            except Exception as e:
                print(f"  WARN {widget}: screenshot failed: {e}")

            print(f"  Generated {widget}.md")


if __name__ == "__main__":
    GENERATED.mkdir(exist_ok=True)
    generate_widget_tables()
    # NOTE: generate_widget_pages requires a display (Qt) and is typically
    # only run in CI with a display server. Skip if no display available.
    import os

    if (
        os.environ.get("DISPLAY")
        or os.environ.get("WAYLAND_DISPLAY")
        or os.name == "nt"
        or "darwin" in os.uname().sysname.lower()
    ):
        generate_widget_pages()
    else:
        print("  SKIP widget page generation (no display)")
    print("Pre-build complete.")
