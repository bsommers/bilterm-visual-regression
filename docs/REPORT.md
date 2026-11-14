# Semantic Visual Regression for bilterm: Report

## 1. Summary

`bilterm-visual-regression` checks bilterm's rendered GUI frames by asking a vision model (TypeSafe Jev System One) questions about them, instead of comparing pixels. This milestone replaced synthetic placeholder images with **real frames rendered by bilterm itself**, rebuilt the questions and assertions around what bilterm actually draws, and added negative and integrity tests. The suite runs offline with 61 passing tests.

**Not done yet:** no call has been made to the live Jev service. Everything model-facing is verified against idealised expected answers (see section 7).

## 2. Use case

bilterm is a TUI multiplexer with a GPU/GUI renderer (`GuiWorkspaceRenderer`). Its rendering is already covered by exact `insta` snapshots and structural tests (e.g. `phase50_gui_render.rs`). Those answer "did any byte change?". They don't answer "does this still look like a two-pane nord workspace with the sessions drawer docked on the left?".

Semantic checks fit three situations:

- **Cross-platform rendering.** Font rasterisation, DPI and GPU/software differences change pixels without changing meaning.
- **Redesigns.** bilterm has 5 visual styles and several themes; the Phase 44 redesign work compared styles by eye. A semantic check can assert invariants (drawer docked left, status bar at bottom, theme identity) while pixels change freely.
- **Release smoke tests.** One coarse "does the GUI look sane" gate that survives cosmetic changes.

## 3. What was built

| Piece | Purpose |
|-------|---------|
| `scripts/capture_frames.sh` | Runs bilterm's existing `examples/design_preview.rs` (headless, real `GuiWorkspaceRenderer`) into a temp target dir, then converts a curated subset. `BILTERM_DIR` selects the checkout. bilterm is not modified. |
| `capture.py`, `scenes.py` | PPM to PNG, `manifest.json` (bilterm commit, per-frame pixel SHA-256, ground truth) and expected-answer JSON. Ground truth is derived from the frame name `<style>__<theme>__<scene>`. |
| 8 real frames in `fixtures/real/` | classic and modern styles, nord and tron-grid themes, single / split / drawer scenes (880x544, 112 KB total). Chosen from the 30 `design_preview` produces. |
| Questions | `session_drawer`, `status_bar` (box); `drawer_visible` (noul); `layout`, `theme`, `style` (choice). Options use bilterm's real vocabulary. |
| Runner and CLI | `verify_drawer`, `verify_status_bar`, `verify_appearance`; `bilterm-vr --verify-drawer/--verify-layout/--verify-theme/--verify-style/--verify-status-bar`. |
| Assertions | New `assert_element_docked`, `assert_choice`, `assert_noul_state`. Existing region and noul helpers kept. |

### What changed from the first commit
The original fixtures modelled a UI bilterm does not have (tabs `terminal / mcp_console / settings`, a floating command-palette modal) and were drawn with Pillow. They were removed, along with their generator. Git history retains them.

## 4. Findings

- **bilterm's frames are deterministic.** Two full `design_preview` runs produced byte-identical output for all 30 frames, so pixel SHA-256 hashes in the manifest are a valid drift detector, and any future label change is a real change.
- **bilterm can already render headlessly to pixels.** `design_preview` needed no GPU or window. This removed the biggest expected blocker (capturing real frames) with no bilterm changes.
- **Label vocabulary mattered.** bilterm's `SplitDirection::Vertical` produces side-by-side panes, which clashes with the original harness's `vertical_split` / `horizontal_split` names. Layout options are now `single_pane` / `side_by_side` / `stacked`, which have no direction ambiguity for a vision model.
- **Measured geometry:** the sessions drawer spans about x = 0 to 270 of 880 px (0.307); the status bar is the last cell row (33/34 = 0.971 down).

## 5. Test strategy (61 tests, about 0.2 s)

1. **Model and assertion unit tests**, including docked and extent edge cases and the uncertain 0.30 to 0.70 noul band.
2. **Real-frame checks**, parametrised from the manifest: layout, theme, style, drawer state and status bar for every frame.
3. **Negative cases**: wrong theme, style, layout; drawer expected-but-absent and present-but-unexpected; a deliberately misplaced drawer box. Each must raise `AssertionError`.
4. **Frame integrity, no model involved:** PNG hash and size match the manifest; frames are not blank; nord frames are brighter than tron-grid frames; the drawer frame's left strip differs from the matching split frame. These check that the ground-truth labels describe the pixels.
5. **Capture round trip:** `convert()` regenerates the committed manifest and expected JSON from the PNGs.

## 6. Benefits

> **Untested.** These are the design's intended benefits. Items that depend on Jev answering correctly (robustness to raster differences, useful failure messages from real model output) are unproven until the live run in section 8. Only the frame-determinism and offline-speed points are measured.

- Survives antialiasing, DPI and platform raster differences that break pixel diffs.
- Failure messages state the semantic problem ("Expected sessions drawer visible, but Jev reported probability=0.030"), not an opaque hash mismatch.
- Real renderer output from a deterministic, GPU-free path, so CI can run it.
- Zero coupling to bilterm's build, tests or release gates.
- Tiny footprint: 8 frames, 112 KB, sub-second offline run.
- Ground truth is checked against pixels, so the labels cannot silently drift from the frames.

## 7. Limitations and honest caveats

- **No live validation.** `<frame>.json` files are *idealised expected answers* derived from ground truth. They are not recorded Jev responses. Passing tests prove the harness logic, not that Jev can answer these questions correctly.
- **The live request shape is unverified, and the endpoint may be wrong.** The client posts to `/v1/ask`. The sibling spec `jev/specs/spacepotatoes-sprite-qa.md` names `https://api.typesafe.ai/v1/systemone`, and the bilterm spec gives no URL. Confirm against TypeSafe's API docs before the first live run.
- **Frames are one fixture scene.** They all show the same sample shell text. Real sessions with dense output, graphs or overlays are not covered.
- **Only 3 of the 5 styles** (classic, modern; snazzy, glass and liquid are not in the curated set) and one pane-count variant.
- **Coarse by design.** This will not catch a 2px misalignment or a subtly wrong colour; keep `insta` snapshots for that.
- **Cost and latency.** Every live check is a network call to a vision model.

## 8. Roadmap

1. **Get a TypeSafe API key and confirm the endpoint and payload** (`TYPESAFE_API_KEY`, `TypeSafe-Danger-Zone-Images: true`), then run: point `TypeSafeClient` at Jev with the 8 frames and compare answers to the expected JSON. Record real responses as fixtures, replacing the idealised ones.
2. **`@pytest.mark.live`** tests, skipped without `TYPESAFE_API_KEY`, so CI stays offline.
3. **Calibrate noul thresholds** (0.70 / 0.30) over repeated runs of the same frames; measure run-to-run variance.
4. **Widen coverage:** snazzy, glass and liquid styles; the agents graph window (`phase50_gui_render` scenes); `stacked` layout; negative frames with deliberately broken UI.
5. **Optionally upstream** a PNG-writing mode to bilterm's `design_preview`, and run a nightly or release-gate job there.

## 9. Reproduce

```bash
pip install -e '.[dev]' && pytest -q                       # 61 passed
BILTERM_DIR=~/src/tools/bilterm scripts/capture_frames.sh  # regenerate; git diff fixtures/real should be empty
```

The committed frames were rendered from bilterm commit `d424638`.
