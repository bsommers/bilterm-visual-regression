"""Ground truth for the real bilterm frames captured by ``design_preview``.

The frame name encodes the scene: ``<style>__<theme>__<scene>`` (e.g. ``classic__nord__drawer``).
Ground truth is derived from that name, so labels cannot drift from the frames they describe.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List

# Curated subset of bilterm's 30 ``design_preview`` frames (5 styles x 2 themes x 3 scenes).
# Covers both layouts, the drawer, two styles and both themes in 8 frames.
CURATED_FRAMES: List[str] = [
    "classic__nord__single",
    "classic__nord__split",
    "classic__nord__drawer",
    "classic__tron-grid__single",
    "classic__tron-grid__drawer",
    "modern__nord__split",
    "modern__nord__drawer",
    "modern__tron-grid__split",
]

# Frame geometry from design_preview: 110x34 cells at 8x16 px -> 880x544.
FRAME_SIZE = (880, 544)
# Measured on the rendered pixels: the session drawer spans x=0..~270 of 880.
DRAWER_RIGHT = 0.307
# Status bar is the last cell row: 1/34 of the height.
STATUS_BAR_TOP = round(33 / 34, 4)


@dataclass(frozen=True)
class SceneTruth:
    frame: str
    style: str
    theme: str  # "nord" | "tron_grid"
    scene: str  # "single" | "split" | "drawer"

    @property
    def layout(self) -> str:
        # "split" and "drawer" scenes both split the focused pane into two side-by-side panes.
        return "single_pane" if self.scene == "single" else "side_by_side"

    @property
    def drawer_visible(self) -> bool:
        return self.scene == "drawer"

    def expected_answers(self) -> Dict[str, Any]:
        """Idealised Jev answers for this frame (NOT recorded from a live model)."""

        def choice(value: str, options: List[str]) -> Dict[str, Any]:
            return {
                "choice": value,
                "confidence": 0.97,
                "probabilities": {o: (0.97 if o == value else round(0.03 / (len(options) - 1), 4)) for o in options},
            }

        from .runner import DEFAULT_TERMINAL_QUESTIONS as Q

        answers: Dict[str, Any] = {
            "layout": choice(self.layout, list(Q["layout"]["criteria"])),
            "theme": choice(self.theme, list(Q["theme"]["criteria"])),
            "style": choice(self.style, list(Q["style"]["criteria"])),
            "drawer_visible": {"probability": 0.96 if self.drawer_visible else 0.03, "confidence": 0.98},
            "status_bar": {"top": STATUS_BAR_TOP, "left": 0.0, "bottom": 1.0, "right": 1.0},
        }
        answers["session_drawer"] = (
            {"top": 0.0, "left": 0.0, "bottom": 1.0, "right": DRAWER_RIGHT}
            if self.drawer_visible
            else {"top": 0.0, "left": 0.0, "bottom": 0.0, "right": 0.0}
        )
        return {"answers": answers}


def parse_frame_name(name: str) -> SceneTruth:
    style, theme, scene = name.split("__")
    return SceneTruth(frame=name, style=style, theme=theme.replace("-", "_"), scene=scene)
