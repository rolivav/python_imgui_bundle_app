"""The "Dog" panel, packaged as a standalone distribution.

A panel is a self-contained piece of ImGui UI: it owns its model, its logic and
its drawing code, and exposes only what a host application needs:

* :attr:`DogPanel.label` - the title of its dockable window;
* :meth:`DogPanel.draw` - the panel content, called once per frame on the GUI
  thread.

The host wraps the panel in a dockable window (so the panel never calls
``imgui.begin()`` / ``imgui.end()`` itself) and gives it a place in its dock
layout; nothing else is required of it.

Inside the distribution the code is split by concern:

* :mod:`dog_panel.dog` - the model: :class:`DogPicture`, plus the decode and
  fetch functions that build it;
* :mod:`dog_panel.dog_panel` - the logic and the UI: :class:`DogPanel`.

The picture is procured by the native ``dog_core`` distribution (HTTP + JSON in
C++); the panel only decodes the returned bytes and draws them. Its remaining
dependencies are ``imgui_bundle``, ``numpy`` and ``Pillow``.
"""

from .dog import DogPicture, decode_picture, fetch_random_dog_picture
from .dog_panel import DogPanel

__all__ = ["DogPicture", "DogPanel", "decode_picture", "fetch_random_dog_picture"]
