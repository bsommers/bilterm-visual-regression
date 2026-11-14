# bilterm-visual-regression

> Semantic visual terminal regression testing and component locator harness powered by **TypeSafe Jev System One** (`jev-latest`).

Target project: `bilterm` (a separate repo; this harness is out-of-band and does not modify it).  
Reference Spec: `specs/bilterm-visual-regression.md` in the `jev` research repo

---

## 1. Why Semantic Visual Regression?

In terminal emulators and GPU-accelerated TUI suites like `bilterm` (e.g. `tests/phase50_gui_render.rs`), traditional pixel-by-pixel image diff snapshots suffer from high fragility:
- **Font Antialiasing & Subpixel Jitter**: Minor subpixel differences between macOS CoreText, FreeType on Linux, and Mesa software rasterizers in headless CI cause byte diff failures.
- **DPI / Retina Scaling**: 1x vs 2x framebuffer rendering alters exact rasterization.
- **Brittle Snapshots**: A 1-pixel shift in an icon or padding invalidates hundreds of golden snapshot files, leading developers to disable visual testing entirely.

### The Jev System One Approach
Instead of matching pixel hashes, `bilterm-visual-regression` sends rendered framebuffer snapshots to TypeSafe's Jev model with semantic questions:
1. **`box`**: Locates the sessions drawer and the status bar as normalized coordinates `[0.0, 1.0]`.
2. **`choice`**: Classifies pane layout (`single_pane` / `side_by_side` / `stacked`), theme (`nord` / `tron_grid`) and visual style (`classic` / `modern`).
3. **`noul`**: Evaluates calibrated probabilistic assertions (`drawer_visible`) with canonical thresholds (`>= 0.70` for True, `<= 0.30` for False).

---

## 2. Architecture & Data Flow

```text
+-----------------------+
|  bilterm (Headless)   |
|  Render Framebuffer   |
+-----------+-----------+
            |
            | PNG Frame Buffer
            v
+-----------------------+     TypeSafe-Danger-Zone-Images: true     +----------------------+
|   bilterm-vr Runner   | ----------------------------------------> | TypeSafe System One  |
|  (Python / Rust CLI)  | <---------------------------------------- |    (Jev 1.14+)       |
+-----------+-----------+        box / choice / noul answers        +----------------------+
            |
            v
+-----------------------+
| Semantic Assertions   |
|  - Center alignment   |
|  - Region containment |
|  - Tab state matches  |
+-----------------------+
```

---

## 3. Status

| Area | State |
|------|-------|
| Real bilterm frames (8 curated, from `design_preview`) | Done, deterministic |
| Assertions, runner, CLI against those frames | Done (mock Jev) |
| Negative cases and pixel-level label checks | Done |
| Live Jev run (8 frames x 3) | Done. layout, style and drawer 100%; **theme unreliable on nord (4/15)**; status bar box coarse |

Read [`docs/REPORT.md`](docs/REPORT.md) for the use case, benefits, limits and roadmap.

## 4. Directory Layout

```
bilterm-visual-regression/
├── fixtures/real/            # 8 real bilterm frames (<name>.png), expected answers (<name>.json), manifest.json
├── scripts/capture_frames.sh # renders frames via bilterm's design_preview example, refreshes fixtures/real
├── src/bilterm_vr/
│   ├── scenes.py             # ground truth derived from <style>__<theme>__<scene> frame names
│   ├── capture.py            # PPM -> PNG + manifest + expected answers
│   ├── client.py             # TypeSafeClient (live) + MockTypeSafeClient
│   ├── runner.py             # questions + verify_drawer / verify_status_bar / verify_appearance
│   ├── assertions.py         # region, docked, choice, noul assertions
│   ├── models.py             # BoundingBox, ChoiceResult, NoulResult
│   └── cli.py                # bilterm-vr
├── fixtures/live/            # recorded real Jev responses (3 runs x 8 frames) + baseline-criteria-v1/
├── scripts/live_check.py     # live run + comparison
├── tests/test_visual_regression.py
├── tests/test_live_recordings.py  # replays recorded Jev responses, pins measured accuracy
└── docs/REPORT.md
```

## 5. Quickstart

```bash
pip install -e '.[dev]'
pytest -v                      # offline, 89 tests, no API key needed
```

Refresh the frames from a bilterm checkout (needs a Rust toolchain; bilterm is not modified):

```bash
BILTERM_DIR=~/src/tools/bilterm scripts/capture_frames.sh
```

Inspect a frame with the CLI (mock mode):

```bash
bilterm-vr fixtures/real/modern__nord__drawer.png --mock \
  --verify-drawer visible --verify-theme nord --verify-style modern --verify-status-bar

bilterm-vr fixtures/real/classic__nord__split.png --mock --json   # full inspection
```

## 6. Live TypeSafe API

```bash
export TYPESAFE_API_KEY="..."
bilterm-vr path/to/frame.png --verify-drawer hidden     # no --mock: sends header TypeSafe-Danger-Zone-Images: true
```

The client posts to `/v1/systemone` following TypeSafe's published `openapi.json`. `scripts/live_check.py --runs 3` reproduces the measurements in [`docs/REPORT.md`](docs/REPORT.md); recorded responses live in `fixtures/live/`.

## 7. Relationship to bilterm

Out-of-band. bilterm keeps its own exact `insta` snapshots; this repo adds a coarse semantic check that needs a network call, so it stays out of bilterm's `cargo test` and CI gates. The only coupling is bilterm's `examples/design_preview.rs`, used read-only. If a PNG-writing mode is ever upstreamed there, `capture_frames.sh` shrinks to a few lines.

## 8. License
Licensed under the [Apache License, Version 2.0](LICENSE).
