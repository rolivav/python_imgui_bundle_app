"""The "Bird" panel, packaged as a standalone distribution.

A panel is a self-contained piece of ImGui UI: it owns its model, its logic and
its drawing code, and exposes only what a host application needs:

* :attr:`BirdPanel.label` - the title of its dockable window;
* :meth:`BirdPanel.draw` - the panel content, called once per frame on the GUI
  thread.

The host wraps the panel in a dockable window (so the panel never calls
``imgui.begin()`` / ``imgui.end()`` itself) and gives it a place in its dock
layout; nothing else is required of it.

Inside the distribution the code is split by concern:

* :mod:`bird_panel.bird` - the model: :class:`BirdPicture`, plus the decode and
  fetch functions that build it;
* :mod:`bird_panel.bird_panel` - the logic and the UI: :class:`BirdPanel`.

The picture is procured by the native ``bird_core`` distribution (HTTP + JSON in
Rust); the panel only decodes the returned bytes and draws them. Its remaining
dependencies are ``imgui_bundle``, ``numpy`` and ``Pillow``.
"""

from .bird import BirdPicture, decode_picture, fetch_random_bird_picture
from .bird_panel import BirdPanel

__all__ = ["BirdPicture", "BirdPanel", "decode_picture", "fetch_random_bird_picture"]
