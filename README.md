# Cat GIFs

A small [Dear ImGui Bundle](https://imgui-bundle.pages.dev/) application whose
frontend is ImGui. It contains a single panel, **Cat**, which displays a random
animated cat GIF fetched from [cataas.com](https://cataas.com/).

When the panel is first shown it fetches a random cat; the **Get Cat** button
fetches a new random one.

Panels are dockable windows inside a full screen dock space, so the panel fills
the whole window on its own, and upcoming panels will share that space (tabs,
splits, freely rearranged by the user).

## Requirements

- [uv](https://docs.astral.sh/uv/) (Python 3.10+ is installed automatically by uv if needed)

## Run

```bash
uv run cat-gifs
```

`uv` creates the virtual environment, installs the dependencies and runs the
app in one step. Equivalent invocations:

```bash
uv run python -m cat_gifs
uv sync && uv run cat-gifs
```

## Project layout

```
src/cat_gifs/
├── app.py                      # window + main loop, draws every registered panel
└── panels/
    ├── __init__.py             # panel registry (add new panels here)
    └── cat_panel/              # the "Cat" panel
        ├── __init__.py         # public API of the panel
        ├── cat_gif.py          # model
        └── cat_panel.py        # logic + UI
```

### Panels are self-contained

Each panel owns its model, its logic and its UI, inside its own package:

| Part  | File           | Contents                                                                                      |
|-------|----------------|-----------------------------------------------------------------------------------------------|
| model | `cat_gif.py`   | `CatGif` — the animation decoded into RGBA frames, plus `decode_gif()` / `fetch_random_cat_gif()` |
| logic | `cat_panel.py` | `CatPanel` — downloads in a background thread, uploads the frames to the GPU, advances the current frame on a timer |
| ui    | `cat_panel.py` | `CatPanel.draw()` — the panel content: the **Get Cat** button and the picture                     |

A panel exposes just `label` (the title of its dockable window) and `draw()`
(its content). Panels never open an ImGui window themselves: `app.py` wraps each
one in a `hello_imgui.DockableWindow`, and hello_imgui calls
`imgui.begin()`/`imgui.end()` around it. That is what makes them dockable.

To add another panel, copy the `cat_panel/` folder, give the new class a unique
`label`, and register it in `panels/__init__.py` (`PANEL_TYPES`). Nothing else
in the app needs to change.

### Docking

`app.py` requests a full screen dock space
(`DefaultImGuiWindowType.provide_full_scr
- The window geometry, the dock layout and the panel visibility are stored by
  hello_imgui in `python_imgui_settings.ini` (see `runner_params.ini_filename`;
  it is written in the working directory by default), which is why `.gitignore`
  ignores `*.ini`. Delete it to fall back to the default layout.een_dock_space`) and places every panel
in `MainDockSpace`:

- with one panel, that space is the whole window, so the panel takes all the
  available space;
- with several, they share it — drag a tab to split the space — and the layout,
  including which panels are visible, is remembered between runs;
- the **View** menu of the menu bar (`show_menu_bar`) lists the panels and can
  restore the default layout, the escape hatch if a panel is closed or lost.

## Notes on the implementation

- The download runs on a worker thread so the GUI never blocks; the result is
  handed back to the GUI thread on the next frame (textures must be created on
  the GUI thread, while the renderer is alive).
- Frames are decoded with Pillow and uploaded once with
  `hello_imgui.create_texture_gpu_from_rgba_data()`; animating a GIF is then
  just a matter of picking the right texture every frame.
- Idling is disabled (`fps_idling.enable_idling = False`) so the GIF keeps
  animating when the mouse is not moving.
