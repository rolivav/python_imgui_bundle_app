"""Panels shown by the application.

Panels are *separate distributions*: each one is self-contained (its own model,
its own logic, its own UI) and is installed like any other dependency - see
``packages/`` for the ones developed next to this app. The application only
needs two things from a panel:

* ``label`` - the title of its dockable window (which is also its tab label, so
  it must be unique among panels);
* ``draw()`` - the panel *content*, called once per frame on the GUI thread.

Panels do not open ImGui windows themselves: each one is registered as a
dockable window (see ``app.py``), and hello_imgui calls ``imgui.begin()`` /
``imgui.end()`` around ``draw()``. That is what makes them dockable, tabbable
and resizable by the user.

Adding a panel therefore takes three steps:

1. Write it as its own distribution (copy ``packages/cat_panel/`` as a starting
   point) exposing a class with a ``label`` and a ``draw()`` method.
2. Add that distribution to the dependencies of this project, with a
   ``[tool.uv.sources]`` entry while it is not published yet.
3. Add its class to :data:`PANEL_TYPES` below.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from cat_panel import CatPanel
from dog_panel import DogPanel


@runtime_checkable
class Panel(Protocol):
    """The contract every panel implements."""

    #: Title of the panel's dockable window. Must be unique among panels.
    label: str

    def draw(self) -> None:
        """Draw the panel content (called once per frame, on the GUI thread)."""
        ...


# Register the panels of the application here.
PANEL_TYPES: tuple[type, ...] = (CatPanel, DogPanel)


def create_panels() -> list[Panel]:
    """Instantiate every registered panel."""
    return [panel_type() for panel_type in PANEL_TYPES]


__all__ = ["CatPanel", "DogPanel", "Panel", "PANEL_TYPES", "create_panels"]
