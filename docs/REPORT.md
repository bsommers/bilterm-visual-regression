# Semantic Visual Regression for bilterm: Report

## 1. Summary

`bilterm-visual-regression` checks bilterm's rendered GUI frames by asking a vision model (TypeSafe Jev System One) questions about them, instead of comparing pixels. This milestone replaced synthetic placeholder images with **real frames rendered by bilterm itself**, rebuilt the questions and assertions around what bilterm actually draws, and added negative and integrity tests. The suite runs offline with 89 passing tests, and it has now been **run live against Jev** (`jev-latest`): 8 frames x 3 runs = 24 calls, per round.

**Headline:** Jev reliably answers *structural* questions (pane layout, visual style, drawer present or absent, drawer position). It is **not** reliable on *palette* identity for the nord theme (4 of 15 correct), and the status bar box is coarse. Details in section 5.

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

## 5. Live results against Jev

Method: `scripts/live_check.py --runs 3`, each of the 8 curated frames three times, raw responses saved in `fixtures/live/` and replayed by `tests/test_live_recordings.py`. About 1,940 input tokens per call.

| Question | Correct | Notes |
|----------|---------|-------|
| `layout` | 24/24 | single_pane vs side_by_side |
| `style` | 24/24 | classic vs modern |
| `drawer_visible` + `session_drawer` box | 24/24 | present: p >= 0.99; absent: p <= 0.22. Drawer right edge 0.28 to 0.33 vs measured 0.307 |
| `status_bar` box | 22/24 | The bar is one row (top = 0.971). Jev boxes about 10% tall (top 0.87 to 0.95), which passes the tolerance. 2 runs of `modern__tron-grid__split` returned top ~0.47 |
| `theme` | 13/24 | tron_grid 9/9; **nord 4/15** |

**Theme problem.** With the first criteria wording ("slate grey-blue background"), the model labelled all 15 nord runs `tron_grid` (theme 9/24). The saved probabilities showed signal: tron frames scored 1.0, nord frames 0.24 to 0.89. After the criteria named the measured background colours (nord `#2E3440`, tron_grid `#020A12`), nord improved only to 4/15. I stopped tuning at two rounds: more iteration on the same 8 frames would mostly overfit and say little about future frames. The baseline responses are kept in `fixtures/live/baseline-criteria-v1/`.

**Not reliable even when "right":**
- The `session_drawer` box on frames **without** a drawer is garbage (various values such as right = 0.08, 0.51 or 0.98). The runner only reads it when `drawer_visible` is true.
- Results vary run to run, but only on the weak questions (theme on nord, the status bar box). The strong ones did not flip across 3 runs.
- The sample is small: 8 frames from one scene with the same shell text, 3 runs each, no confidence intervals.

**What to do with this today**
- Use `layout`, `style` and `drawer_visible` as semantic gates.
- Do **not** gate on `theme` for nord. For palette identity use a deterministic pixel check (the dominant background colour is `#2e3440` or `#020a12`), which the integrity tests already do offline.
- Treat the status bar box as "somewhere along the bottom", not as a position measurement.

## 6. Test strategy (89 tests, about 0.2 s)

1. **Model and assertion unit tests**, including docked and extent edge cases and the uncertain 0.30 to 0.70 noul band.
2. **Real-frame checks**, parametrised from the manifest: layout, theme, style, drawer state and status bar for every frame.
3. **Negative cases**: wrong theme, style, layout; drawer expected-but-absent and present-but-unexpected; a deliberately misplaced drawer box. Each must raise `AssertionError`.
4. **Frame integrity, no model involved:** PNG hash and size match the manifest; frames are not blank; nord frames are brighter than tron-grid frames; the drawer frame's left strip differs from the matching split frame. These check that the ground-truth labels describe the pixels.
5. **Capture round trip:** `convert()` regenerates the committed manifest and expected JSON from the PNGs.

## 7. Benefits

> **Partly tested.** Measured: frame determinism, offline speed, and Jev's accuracy on layout, style and drawer (section 5). **Still untested:** robustness to cross-platform raster differences, which needs frames from a second platform or renderer, and anything beyond these 8 frames.

- Survives antialiasing, DPI and platform raster differences that break pixel diffs.
- Failure messages state the semantic problem ("Expected sessions drawer visible, but Jev reported probability=0.030"), not an opaque hash mismatch.
- Real renderer output from a deterministic, GPU-free path, so CI can run it.
- Zero coupling to bilterm's build, tests or release gates.
- Tiny footprint: 8 frames, 112 KB, sub-second offline run.
- Ground truth is checked against pixels, so the labels cannot silently drift from the frames.

## 8. Limitations and honest caveats

- **Two kinds of fixture.** `fixtures/real/<frame>.json` are *idealised expected answers* derived from ground truth, not Jev output; tests using them prove harness logic only. `fixtures/live/` holds real Jev responses (section 5).
- **The first client was wrong.** It posted to `/v1/ask` (404) with an `options` list and a data-URI asset (422). The live API is `/v1/systemone`, with `criteria` maps and `format` + `data_base64` assets. The client now follows TypeSafe's published `openapi.json`, and a wire-format test pins it.
- **Frames are one fixture scene.** They all show the same sample shell text. Real sessions with dense output, graphs or overlays are not covered.
- **Only 3 of the 5 styles** (classic, modern; snazzy, glass and liquid are not in the curated set) and one pane-count variant.
- **Coarse by design.** This will not catch a 2px misalignment or a subtly wrong colour; keep `insta` snapshots for that.
- **Cost and latency.** Every live check is a network call to a vision model.

## 9. Roadmap

1. ~~Live run~~ Done (section 5).
2. **Fix the theme question.** Try a pairwise comparison against a reference frame, or a tighter `choice` with a worked description; validate on *new* frames, not the 8 used for tuning. Or drop it in favour of the pixel check.
3. **`@pytest.mark.live`** tests, skipped without `TYPESAFE_API_KEY`, so CI stays offline.
4. **Calibrate noul thresholds** (0.70 / 0.30): hidden-drawer probabilities reached 0.22, close enough to 0.30 to watch. Needs more frames.
5. **Widen coverage:** snazzy, glass and liquid styles; the agents graph window (`phase50_gui_render` scenes); `stacked` layout; negative frames with deliberately broken UI.
6. **Optionally upstream** a PNG-writing mode to bilterm's `design_preview`, and run a nightly or release-gate job there.

## 10. Reproduce

```bash
pip install -e '.[dev]' && pytest -q                       # 89 passed
BILTERM_DIR=~/src/tools/bilterm scripts/capture_frames.sh  # regenerate; git diff fixtures/real should be empty
TYPESAFE_API_KEY=... python3 scripts/live_check.py --runs 3  # live run (needs a key; ~24 calls)
```

The committed frames were rendered from bilterm commit `d424638`.
