# Todool

![preview](showcase/todool_preview.png)

I developed [Todool](https://todool.de/) fulltime from 2022-2023 in [odin](https://odin-lang.org/). I started selling it in November 2022 but quickly felt a bit of burnout. Lot's of reworks lead to the current state of things, which I feel like reworking again... 

Instead of letting the project die completly I'll share the source here, have fun with it!

## What I'd rework

- Renderer: compute tiled sdf renderer to save up on rerendering
- UI: immediate style to be more detatched from the data
- DB: store the editor content in a database and write out a readable text file that ppl can have as a backup or git inspection
- Kanban: remove kanban and focus solely on "List Mode" and make that better

## Tech

- OpenGL 3.3 renderer similar to 4coder
- SDL2
- fontstash - glyph atlas [fontstash](https://github.com/memononen/fontstash)
- RMGUI - similar to [luigi](https://github.com/nakst/luigi/blob/main/luigi.h)
- Undo/Redo with callbacks (not that nice)
- Custom binary file format (trash)

## How To Build

Install [Odin](https://odin-lang.org/docs/install/) based on your platform. Built and tested with Odin `dev-2026-09`.

### macOS

```sh
brew install odin sdl2 sdl2_mixer
make -C src/tfd      # builds src/tfd/main-darwin.a
make app             # optimized build -> target/Todool.app
```

`make app` bundles the Homebrew dylibs (SDL2, SDL3, SDL2_mixer and their codec dependencies) into the app, so `target/Todool.app` runs without Homebrew. It is ad-hoc signed and arm64 only (Homebrew libraries are arm64). Downloaded copies are quarantined by Gatekeeper, so open them with right click -> Open.

For quick iteration use `make build` (builds and runs `target/todool`, needs the Homebrew libraries) or `make check` (type check only).

### Prepare Static Libraries (Linux)

1. Build stb truetype -> go to `odin/vendor/stb/src/` and run `./build_stb.sh` in there (Odin releases may already ship the libraries)
2. Build -> go to `src/tfd` and run `make` in there

### Todool

1. Clone this repository.
2. Create a `target` folder next to the `src` folder
3. On Windows: run `build.bat` - On Linux: run `make`
