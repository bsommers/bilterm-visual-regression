# bilterm-visual-regression

> Semantic visual terminal regression testing and component locator harness powered by **TypeSafe Jev System One** (`jev-latest`).

Target Project Reference: [`/Users/bill/src/tools/bilterm`](file:///Users/bill/src/tools/bilterm)  
Reference Spec: [`specs/bilterm-visual-regression.md`](file:///Users/bill/src/research/ai-ml/jev/specs/bilterm-visual-regression.md)

---

## 1. Why Semantic Visual Regression?

In terminal emulators and GPU-accelerated TUI suites like `bilterm` (e.g. `tests/phase50_gui_render.rs`), traditional pixel-by-pixel image diff snapshots suffer from high fragility:
- **Font Antialiasing & Subpixel Jitter**: Minor subpixel differences between macOS CoreText, FreeType on Linux, and Mesa software rasterizers in headless CI cause byte diff failures.
- **DPI / Retina Scaling**: 1x vs 2x framebuffer rendering alters exact rasterization.
- **Brittle Snapshots**: A 1-pixel shift in an icon or padding invalidates hundreds of golden snapshot files, leading developers to disable visual testing entirely.

### The Jev System One Approach
Instead of matching pixel hashes, `bilterm-visual-regression` sends rendered framebuffer snapshots to TypeSafe's Jev model with semantic questions:
1. **`box`**: Locates floating command palettes, split pane borders, active search bars, and tabs as normalized coordinates `[0.0, 1.0]`.
2. **`choice`**: Classifies active tab selections (`["terminal", "mcp_console", "settings"]`), theme palettes (`["tron", "classic", "dark", "light"]`), and pane layouts (`["single", "horizontal_split", "vertical_split"]`).
3. **`noul`**: Evaluates calibrated probabilistic assertions (`modal_visible`, `cursor_blink_visible`) with canonical thresholds (`>= 0.70` for True, `<= 0.30` for False).

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

## 3. Directory Layout

```
bilterm-visual-regression/
├── fixtures/                         # Synthetic terminal snapshots and recorded Jev mock fixtures
│   ├── terminal_normal.png
│   ├── terminal_normal.json
│   ├── terminal_modal_palette.png
│   ├── terminal_modal_palette.json
│   ├── terminal_settings_tab.png
│   ├── terminal_settings_tab.json
│   ├── terminal_mcp_tab.png
│   ├── terminal_mcp_tab.json
│   ├── terminal_tron_theme.png
│   └── terminal_tron_theme.json
├── src/
│   └── bilterm_vr/
│       ├── __init__.py               # Top-level exports
│       ├── assertions.py             # assert_element_in_region, assert_active_tab, etc.
│       ├── cli.py                    # Standalone CLI utility
│       ├── client.py                 # Live TypeSafeClient + MockTypeSafeClient
│       ├── generate_fixtures.py      # Pillow-based synthetic terminal frame generator
│       ├── models.py                 # BoundingBox, ChoiceResult, NoulResult
│       └── runner.py                 # VisualRegressionRunner test harness
├── tests/
│   └── test_visual_regression.py     # Pytest suite verifying models, assertions, and fixtures
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## 4. Quickstart & Installation

```bash
cd /Users/bill/src/research/ai-ml/jev-usecases/bilterm-visual-regression

# Install dependencies
pip install -e .

# Or using requirements.txt
pip install -r requirements.txt
```

### Running Tests (Offline / Mock Mode)
Run the automated test suite against recorded fixtures and synthetic terminal frames:

```bash
pytest -v
```

### Running the CLI
Inspect a rendered terminal frame:

```bash
# Verify that a command palette modal is centered in the screen
bilterm-vr fixtures/terminal_modal_palette.png --mock --verify-modal

# Verify active tab selection
bilterm-vr fixtures/terminal_settings_tab.png --mock --verify-tab settings

# Run full visual inspection with JSON output
bilterm-vr fixtures/terminal_tron_theme.png --mock --json
```

---

## 5. Live TypeSafe API Integration

To run against the live TypeSafe System One API:

```bash
export TYPESAFE_API_KEY="your-typesafe-api-key"

# Omit --mock flag to dispatch live requests with header TypeSafe-Danger-Zone-Images: true
bilterm-vr path/to/rendered_frame.png --verify-modal
```

### Example Live Payload

```json
{
  "model": "jev-latest",
  "state": {
    "terminal_frame": "frame-001"
  },
  "assets": {
    "frame-001": {
      "type": "image",
      "part": "screen_capture",
      "data": "data:image/png;base64,..."
    }
  },
  "questions": {
    "command_palette": {
      "type": "box",
      "instructions": "the command input window in `terminal_frame`"
    },
    "active_tab": {
      "type": "choice",
      "options": ["terminal", "mcp_console", "settings"],
      "instructions": "which tab header is currently highlighted?"
    },
    "modal_visible": {
      "type": "noul",
      "instructions": "is there an overlay or modal dialog visible?"
    }
  }
}
```

---

## 6. How to Integrate into `bilterm` (Rust / Cargo Pipeline)

In `bilterm/tests/phase50_gui_render.rs`, export the rendered frame buffer to a temporary PNG and call `bilterm-vr`:

```rust
#[test]
fn test_command_palette_modal_spatial_centering() {
    let mut terminal = BiltermTestHarness::new_headless(1200, 800);
    terminal.send_key_combination(KeyCode::Ctrl, 'p');
    let frame_png_path = terminal.capture_frame_png("target/tmp_palette_frame.png");

    let status = std::process::Command::new("bilterm-vr")
        .arg(&frame_png_path)
        .arg("--verify-modal")
        .status()
        .expect("Failed to execute bilterm-vr");

    assert!(status.success(), "Command palette modal failed visual regression verification");
}
```

---

## 7. License
MIT
