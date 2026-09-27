"""Panels shown by the application.

A panel is **self-contained**: it keeps its own model, its own logic and its
own UI inside its own package. The only thing the application has to know about
a panel is its ``draw()`` method, which is called once per frame (on the GUI
thread).

Adding a new panel therefore only takes two steps:

1. Drop a new package in this folder (copy ``cat_panel/`` as a starting point)
   exposing a class with a ``draw()`` method.
2. Add that class to :data:`PANEL_TYPES` below.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .cat_panel import CatPanel


@runtime_checkable
class Panel(Protocol):
    """The contract every panel implements."""

    def draw(self) -> None:
        """Draw the panel (called once per frame, on the GUI thread)."""
        ...


# Register the panels of the application here.
PANEL_TYPES: tuple[type, ...] = (CatPanel,)


def create_panels() -> list[Panel]:
    """Instantiate every registered panel."""
    return [panel_type() for panel_type in PANEL_TYPES]


__all__ = ["CatPanel", "Panel", "PANEL_TYPES", "create_panels"]
