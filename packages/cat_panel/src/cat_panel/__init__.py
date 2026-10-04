"""The "Cat" panel, packaged as a standalone distribution.

A panel is a self-contained piece of ImGui UI: it owns its model, its logic and
its drawing code, and exposes only what a host application needs:

* :attr:`CatPanel.label` - the title of its dockable window;
* :meth:`CatPanel.draw` - the panel content, called once per frame on the GUI
  thread.

The host wraps the panel in a dockable window (so the panel never calls
``imgui.begin()`` / ``imgui.end()`` itself) and gives it a place in its dock
layout; nothing else is required of it.

Inside the distribution the code is split by concern:

* :mod:`cat_panel.cat_gif` - the model: :class:`CatGif`, plus the download and
  decode functions that build it;
* :mod:`cat_panel.cat_panel` - the logic and the UI: :class:`CatPanel`.

Its only dependencies are ``imgui_bundle``, ``numpy``, ``Pillow`` and
``requests``.
"""

from .cat_gif import CatGif, fetch_random_cat_gif
from .cat_panel import CatPanel

__all__ = ["CatGif", "CatPanel", "fetch_random_cat_gif"]
