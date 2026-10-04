"""Native image procurement for the Bird panel.

The Rust core (:mod:`bird_core._bird_core`) asks the `Ornithophile
<https://github.com/tustoz/ornithophile>`_ API for a bird and downloads its
picture. This module only gives that a Pythonic shape.
"""

from __future__ import annotations

from typing import NamedTuple

from bird_core._bird_core import fetch_random_bird as _fetch_random_bird


class BirdImage(NamedTuple):
    """The encoded picture, plus what the API says about the bird."""

    data: bytes
    name: str  # common name, e.g. "House Wren"
    sci_name: str  # scientific name, e.g. "Troglodytes aedon"
    url: str  # where the picture was downloaded from


def fetch_random_bird() -> BirdImage:
    """Fetch a random bird picture from the Ornithophile API.

    Blocking: call it from a worker thread (see
    :meth:`bird_panel.BirdPanel.request_new_bird`). The Rust core releases the GIL
    while the network I/O is in flight.

    No API key is involved. The data is under Ornithophile's academic,
    non-commercial licence (see the distribution's README).
    """
    data, name, sci_name, url = _fetch_random_bird()
    return BirdImage(data=data, name=name, sci_name=sci_name, url=url)


__all__ = ["BirdImage", "fetch_random_bird"]
