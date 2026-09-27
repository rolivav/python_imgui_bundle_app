"""The "Cat" panel: shows random animated cat GIFs from https://cataas.com/.

The panel is a self-contained package, split by concern:

* :mod:`~cat_gifs.panels.cat_panel.cat_gif` — the model: :class:`CatGif`, plus
  the download/decode functions that build it.
* :mod:`~cat_gifs.panels.cat_panel.cat_panel` — the logic and the UI:
  :class:`CatPanel`.

Its only dependencies are ``imgui_bundle``, ``numpy``, ``Pillow`` and
``requests``, so the whole folder can be copied into another Dear ImGui Bundle
application as is.
"""

from .cat_gif import CatGif, fetch_random_cat_gif
from .cat_panel import CatPanel

__all__ = ["CatGif", "CatPanel", "fetch_random_cat_gif"]
