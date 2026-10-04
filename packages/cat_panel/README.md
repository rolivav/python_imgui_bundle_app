# cat-panel

The **Cat** panel of the *Zoo App* application, packaged on its own so that the
application depends on it the same way it depends on any other distribution.

A panel is a self-contained piece of ImGui UI. It exposes exactly two things:

| Member   | Meaning                                                              |
|----------|----------------------------------------------------------------------|
| `label`  | title of the panel's dockable window (also its tab label)             |
| `draw()` | the panel content, called once per frame on the GUI thread            |

It never opens an ImGui window itself — the host wraps it in a dockable window
(so `imgui.begin()` / `imgui.end()` are managed by the host) and places it in its
dock layout.

```python
from cat_panel import CatPanel

panel = CatPanel()   # panel.label == "Cat"
panel.draw()         # call inside the host's imgui.begin()/imgui.end()
```

Inside the package the code is split by concern:

- `cat_gif.py` — the model: `CatGif` (an animation decoded into RGBA frames) plus
  `decode_gif()` / `fetch_random_cat_gif()`.
- `cat_panel.py` — the logic and the UI: `CatPanel` (background download, GPU
  upload, frame timing, drawing).

## Installing

```bash
uv add cat-panel                                  # from a package index
uv add cat-panel --path ../cat_panel --editable   # from a local folder
```

## Building a wheel

```bash
uv build            # from this folder: writes dist/cat_panel-0.1.0-py3-none-any.whl
```

The wheel can then be uploaded to a package index and installed by name.
