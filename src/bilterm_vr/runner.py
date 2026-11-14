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
    assert_element_docked,
    assert_choice,
    assert_noul_state,
    Region,
)


DEFAULT_TERMINAL_QUESTIONS = {
    "session_drawer": {
        "type": "box",
        "instructions": (
            "the sessions drawer in `terminal_frame`: a full-height side panel listing "
            "SESSION entries. Answer an empty box if there is no such panel"
        ),
    },
    "status_bar": {
        "type": "box",
        "instructions": "the status bar: the single-row strip along the bottom edge of `terminal_frame`",
    },
    "drawer_visible": {
        "type": "noul",
        "instructions": "is the sessions drawer (a side panel listing SESSION entries) visible in `terminal_frame`?",
    },
    "layout": {
        "type": "choice",
        "options": ["single_pane", "side_by_side", "stacked"],
        "instructions": (
            "how are the terminal panes arranged? Ignore the sessions drawer; count only panes "
            "that contain shell output"
        ),
    },
    "theme": {
        "type": "choice",
        "options": ["nord", "tron_grid"],
        "instructions": (
            "which palette is rendered? nord = slate grey-blue background; "
            "tron_grid = near-black navy background with cyan and orange accents"
        ),
    },
    "style": {
        "type": "choice",
        "options": ["classic", "modern"],
        "instructions": (
            "which visual style? classic = bracketed pane titles like `[1] PANE #1` and a "
            "`3270-OIA` status bar; modern = three-dot window header and a flat status bar"
        ),
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
                        if json_file.stem == "manifest":
                            continue
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

    def verify_drawer(
        self,
        image_path: Path | str,
        expected_visible: bool = True,
    ) -> VisualInspectionResult:
        """Assert the sessions drawer is present (docked on the left) or absent."""
        qs = {k: DEFAULT_TERMINAL_QUESTIONS[k] for k in ("drawer_visible", "session_drawer")}
        result = self.run_check(image_path, questions=qs)
        res = result.get_noul("drawer_visible")
        assert res is not None, "Missing drawer_visible in response"
        assert_noul_state(res, expected_visible, "sessions drawer")

        if expected_visible:
            box = result.get_box("session_drawer")
            assert box is not None, "Expected session_drawer box when drawer is visible"
            assert_element_in_region(box, Region.LEFT_HALF)
            assert_element_docked(box, edge="left", max_extent=0.45)
        return result

    def verify_status_bar(self, image_path: Path | str) -> VisualInspectionResult:
        result = self.run_check(image_path, questions={"status_bar": DEFAULT_TERMINAL_QUESTIONS["status_bar"]})
        box = result.get_box("status_bar")
        assert box is not None, "Missing status_bar in response"
        assert_element_in_region(box, Region.STATUS_BAR)
        assert_element_docked(box, edge="bottom", max_extent=0.15)
        return result

    def verify_appearance(
        self,
        image_path: Path | str,
        layout: Optional[str] = None,
        theme: Optional[str] = None,
        style: Optional[str] = None,
    ) -> VisualInspectionResult:
        """Assert any combination of pane layout, theme palette and visual style."""
        expected = {"layout": layout, "theme": theme, "style": style}
        qs = {k: DEFAULT_TERMINAL_QUESTIONS[k] for k, v in expected.items() if v is not None}
        if not qs:
            raise ValueError("verify_appearance needs at least one of layout/theme/style")
        result = self.run_check(image_path, questions=qs)
        for name, want in expected.items():
            if want is None:
                continue
            got = result.get_choice(name)
            assert got is not None, f"Missing {name} in response"
            assert_choice(got, want, name)
        return result
