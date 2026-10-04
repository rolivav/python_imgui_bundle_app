# bird-panel

The "Bird" panel: a dockable window that shows a random bird picture, fetched
from the [Ornithophile API](https://github.com/tustoz/ornithophile) by the native
`bird-core` distribution (HTTP + JSON in Rust).

Like every panel it is self-contained — model, logic and UI — and only exposes a
`label` and a `draw()` method to the host application. Inside the distribution:

| Module | Contents |
|---|---|
| `bird_panel.bird` | the model: `BirdPicture`, `decode_picture()`, `fetch_random_bird_picture()` |
| `bird_panel.bird_panel` | the logic and the UI: `BirdPanel` |

The download runs on a worker thread so the GUI never blocks; the picture is
uploaded to the GPU on the next frame.

## Requirements

`bird-core` needs no API key; it reads its bird data from
[Ornithophile](https://github.com/tustoz/ornithophile) (under an academic,
non-commercial licence — see that distribution's README) and needs `curl` on
`PATH` at runtime.

## Installing

```bash
uv add bird-panel                                  # from a package index
uv add bird-panel --path ../bird_panel --editable  # from a local folder
```
