# dog-panel

The **Dog** panel of the *Cat GIFs* application, packaged on its own so that the
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
from dog_panel import DogPanel

panel = DogPanel()   # panel.label == "Dog"
panel.draw()         # call inside the host's imgui.begin()/imgui.end()
```

Inside the package the code is split by concern:

- `dog.py` — the model: `DogPicture` (a picture decoded into RGBA pixels, with
  its breed) plus `decode_picture()` / `fetch_random_dog_picture()`.
- `dog_panel.py` — the logic and the UI: `DogPanel` (background download, GPU
  upload, drawing).

## Where the pictures come from

The picture is procured by the native [`dog-core`](../dog_core/) distribution,
which performs the HTTP requests to the [dog.ceo](https://dog.ceo/dog-api/) API
and the JSON parsing in C++: `https://dog.ceo/api/breeds/image/random` → the URL
of a random picture → the downloaded bytes → the breed derived from the URL
(e.g. `.../breeds/hound-afghan/...` → *Afghan Hound*). This package only decodes
those bytes with Pillow and draws the result.

## Installing

```bash
uv add dog-panel                                  # from a package index
uv add dog-panel --path ../dog_panel --editable   # from a local folder
```

## Building a wheel

```bash
uv build            # from this folder: writes dist/dog_panel-0.1.0-py3-none-any.whl
```

The wheel can then be uploaded to a package index and installed by name.
