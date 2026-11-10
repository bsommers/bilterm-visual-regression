"""Synthetic terminal window frame generator for bilterm test fixtures."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def draw_terminal_base(
    width: int = 1000,
    height: int = 600,
    bg_color: str = "#121212",
    tab_active: str = "terminal",
    prompt_text: str = "bill@macbook ~/src/tools/bilterm $ cargo test --release",
    status_text: str = " NORMAL | utf-8 | 120x40 | latency: 0.8ms ",
) -> Image.Image:
    """Draw a base terminal window with tab bar, content area, prompt, and status bar."""
    img = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    # 1. Header Tab bar (y: 0 to 40)
    tab_bar_h = 40
    draw.rectangle([0, 0, width, tab_bar_h], fill="#1e1e1e")

    # Draw tabs
    tabs = ["terminal", "mcp_console", "settings"]
    tab_x = 10
    tab_w = 120
    for tab in tabs:
        is_active = (tab == tab_active)
        tab_bg = "#2d2d2d" if is_active else "#181818"
        text_color = "#ffffff" if is_active else "#888888"
        draw.rectangle([tab_x, 6, tab_x + tab_w, tab_bar_h], fill=tab_bg)
        draw.text((tab_x + 12, 14), tab.upper(), fill=text_color)
        tab_x += tab_w + 8

    # 2. Terminal content area: prompt and shell output
    draw.text((20, 60), prompt_text, fill="#00ff66")
    draw.text((20, 90), "   Compiling bilterm v0.1.0 (/Users/bill/src/tools/bilterm)", fill="#cccccc")
    draw.text((20, 115), "    Finished release [optimized] target(s) in 2.34s", fill="#cccccc")
    draw.text((20, 140), "     Running unittests src/lib.rs", fill="#cccccc")
    draw.text((20, 165), "test render::tests::test_pipeline_init ... ok", fill="#88ff88")
    draw.text((20, 190), "test input::tests::test_key_dispatch ... ok", fill="#88ff88")
    draw.text((20, 220), "bill@macbook ~/src/tools/bilterm $ █", fill="#00ff66")

    # 3. Status bar at bottom (y: height - 30 to height)
    status_y = height - 30
    draw.rectangle([0, status_y, width, height], fill="#264f78")
    draw.text((10, status_y + 8), status_text, fill="#ffffff")

    return img


def add_command_palette_modal(
    base_img: Image.Image,
    query_text: str = "> search files or execute command...",
) -> Image.Image:
    """Overlay a centered command palette modal dialog onto the terminal frame."""
    img = base_img.copy()
    width, height = img.size

    # Normalized bounds: left ~ 0.26, right ~ 0.74, top ~ 0.28, bottom ~ 0.52
    modal_left = int(width * 0.26)
    modal_top = int(height * 0.28)
    modal_right = int(width * 0.74)
    modal_bottom = int(height * 0.52)

    # Semi-transparent backdrop / shadow effect
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 100))
    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))

    draw = ImageDraw.Draw(img)
    # Modal frame
    draw.rectangle(
        [modal_left, modal_top, modal_right, modal_bottom],
        fill="#1f232a",
        outline="#4f97d7",
        width=2,
    )

    # Modal input field
    input_box = [modal_left + 15, modal_top + 15, modal_right - 15, modal_top + 45]
    draw.rectangle(input_box, fill="#121417", outline="#61afef", width=1)
    draw.text((modal_left + 25, modal_top + 22), query_text, fill="#e5c07b")

    # Sample result rows
    draw.text((modal_left + 25, modal_top + 55), "1. bilterm::config::load_theme", fill="#ffffff")
    draw.text((modal_left + 25, modal_top + 78), "2. bilterm::gpu::create_swapchain", fill="#aaaaaa")
    draw.text((modal_left + 25, modal_top + 101), "3. bilterm::tui::split_vertical", fill="#aaaaaa")

    return img


def generate_all_fixtures(output_dir: Path | str) -> None:
    """Generate all synthetic fixture PNGs and matching recorded JSON mock responses."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Base terminal frame (tab: terminal, theme: dark, no modal)
    f1 = draw_terminal_base(tab_active="terminal")
    f1.save(out_dir / "terminal_normal.png")

    # 2. Command palette modal visible (centered dialog)
    f2 = add_command_palette_modal(f1)
    f2.save(out_dir / "terminal_modal_palette.png")

    # 3. Settings tab active
    f3 = draw_terminal_base(tab_active="settings")
    f3.save(out_dir / "terminal_settings_tab.png")

    # 4. MCP console tab active
    f4 = draw_terminal_base(tab_active="mcp_console")
    f4.save(out_dir / "terminal_mcp_tab.png")

    # 5. Tron theme frame (cyan/magenta styling)
    f5 = draw_terminal_base(
        bg_color="#001122",
        prompt_text="grid@tron-system:~$ v-sync --tron-glow",
        status_text=" TRON PROTOCOL | 120 FPS | 100% NEON ",
    )
    f5.save(out_dir / "terminal_tron_theme.png")


if __name__ == "__main__":
    generate_all_fixtures("fixtures")
    print("Fixtures generated successfully.")
