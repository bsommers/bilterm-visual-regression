"""Visual regression runner orchestrating test suites on rendered terminal frames."""

from __future__ import annotations
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from .models import VisualInspectionResult
from .client import BaseTypeSafeClient, TypeSafeClient, MockTypeSafeClient
from .assertions import (
    assert_element_in_region,
    assert_element_centered_horizontally,
    assert_active_tab,
    assert_modal_state,
    Region,
)


DEFAULT_TERMINAL_QUESTIONS = {
    "command_palette": {
        "type": "box",
        "instructions": "the command input window in `terminal_frame`",
    },
    "active_tab": {
        "type": "choice",
        "options": ["terminal", "mcp_console", "settings"],
        "instructions": "which tab header is currently highlighted?",
    },
    "modal_visible": {
        "type": "noul",
        "instructions": "is there an overlay or modal dialog visible?",
    },
    "theme": {
        "type": "choice",
        "options": ["tron", "classic", "dark", "light"],
        "instructions": "which color theme or palette is rendered in `terminal_frame`?",
    },
    "split_layout": {
        "type": "choice",
        "options": ["single", "horizontal_split", "vertical_split"],
        "instructions": "what is the terminal pane layout?",
    },
}


class VisualRegressionRunner:
    """Executes visual regression checks across terminal screenshot buffers."""

    def __init__(
        self,
        client: Optional[BaseTypeSafeClient] = None,
        use_mock: bool = False,
        fixtures_dir: Optional[Path | str] = None,
    ):
        if client:
            self.client = client
        elif use_mock or not os.environ.get("TYPESAFE_API_KEY"):
            # Load fixtures if available
            fixtures_map = {}
            if fixtures_dir:
                f_dir = Path(fixtures_dir)
                if f_dir.exists():
                    for json_file in f_dir.glob("*.json"):
                        try:
                            with open(json_file, "r") as f:
                                fixtures_map[json_file.stem] = json.load(f)
                        except Exception:
                            pass
            self.client = MockTypeSafeClient(fixtures_map=fixtures_map)
        else:
            self.client = TypeSafeClient()

    def run_check(
        self,
        image_path: Path | str,
        questions: Optional[Dict[str, Any]] = None,
    ) -> VisualInspectionResult:
        qs = questions or DEFAULT_TERMINAL_QUESTIONS
        return self.client.inspect_frame(image_path, qs)

    def verify_modal_dialog_centered(
        self,
        image_path: Path | str,
        expected_visible: bool = True,
    ) -> VisualInspectionResult:
        result = self.run_check(
            image_path,
            questions={
                "command_palette": DEFAULT_TERMINAL_QUESTIONS["command_palette"],
                "modal_visible": DEFAULT_TERMINAL_QUESTIONS["modal_visible"],
            },
        )
        modal_res = result.get_noul("modal_visible")
        assert modal_res is not None, "Missing modal_visible question in response"
        assert_modal_state(modal_res, expected_visible)

        if expected_visible:
            box = result.get_box("command_palette")
            assert box is not None, "Expected command_palette box when modal is visible"
            assert_element_centered_horizontally(box)
            assert_element_in_region(box, Region.CENTER)

        return result

    def verify_active_tab_and_theme(
        self,
        image_path: Path | str,
        expected_tab: str,
        expected_theme: Optional[str] = None,
    ) -> VisualInspectionResult:
        qs = {"active_tab": DEFAULT_TERMINAL_QUESTIONS["active_tab"]}
        if expected_theme:
            qs["theme"] = DEFAULT_TERMINAL_QUESTIONS["theme"]

        result = self.run_check(image_path, questions=qs)
        tab_res = result.get_choice("active_tab")
        assert tab_res is not None, "Missing active_tab in response"
        assert_active_tab(tab_res, expected_tab)

        if expected_theme:
            theme_res = result.get_choice("theme")
            assert theme_res is not None, "Missing theme in response"
            assert (
                theme_res.choice == expected_theme
            ), f"Expected theme '{expected_theme}', got '{theme_res.choice}'"

        return result
