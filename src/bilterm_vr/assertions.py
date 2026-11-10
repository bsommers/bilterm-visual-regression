"""Assertion helpers for semantic visual regression in terminal buffers."""

from __future__ import annotations
from enum import Enum
from typing import Union, Tuple
from .models import BoundingBox, ChoiceResult, NoulResult


class Region(str, Enum):
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"
    CENTER = "center"
    TOP_HALF = "top_half"
    BOTTOM_HALF = "bottom_half"
    LEFT_HALF = "left_half"
    RIGHT_HALF = "right_half"
    HEADER = "header"        # top ~10%
    STATUS_BAR = "status_bar"# bottom ~10%


def assert_element_in_region(
    box: BoundingBox,
    region: Union[Region, str, Tuple[float, float, float, float]],
    margin: float = 0.05
) -> None:
    """Assert that a BoundingBox falls within the specified spatial region or quadrant.

    Args:
        box: The bounding box returned by Jev.
        region: A Region enum, quadrant name, or (min_x, min_y, max_x, max_y) normalized rect.
        margin: Allowed tolerance boundary.
    """
    if isinstance(region, (list, tuple)) and len(region) == 4:
        min_x, min_y, max_x, max_y = region
    else:
        reg_str = region.value if isinstance(region, Region) else str(region).lower()
        if reg_str == "top_left":
            min_x, min_y, max_x, max_y = (0.0, 0.0, 0.55, 0.55)
        elif reg_str == "top_right":
            min_x, min_y, max_x, max_y = (0.45, 0.0, 1.0, 0.55)
        elif reg_str == "bottom_left":
            min_x, min_y, max_x, max_y = (0.0, 0.45, 0.55, 1.0)
        elif reg_str == "bottom_right":
            min_x, min_y, max_x, max_y = (0.45, 0.45, 1.0, 1.0)
        elif reg_str == "center":
            min_x, min_y, max_x, max_y = (0.15, 0.15, 0.85, 0.85)
        elif reg_str == "top_half":
            min_x, min_y, max_x, max_y = (0.0, 0.0, 1.0, 0.55)
        elif reg_str == "bottom_half":
            min_x, min_y, max_x, max_y = (0.0, 0.45, 1.0, 1.0)
        elif reg_str == "left_half":
            min_x, min_y, max_x, max_y = (0.0, 0.0, 0.55, 1.0)
        elif reg_str == "right_half":
            min_x, min_y, max_x, max_y = (0.45, 0.0, 1.0, 1.0)
        elif reg_str == "header":
            min_x, min_y, max_x, max_y = (0.0, 0.0, 1.0, 0.18)
        elif reg_str == "status_bar":
            min_x, min_y, max_x, max_y = (0.0, 0.82, 1.0, 1.0)
        else:
            raise ValueError(f"Unknown region specifier: {region}")

    cx = box.center_x
    cy = box.center_y

    assert (min_x - margin) <= cx <= (max_x + margin), (
        f"Element center_x={cx:.3f} outside expected horizontal range [{min_x - margin:.3f}, {max_x + margin:.3f}] "
        f"for region '{region}' (box: left={box.left:.3f}, right={box.right:.3f})"
    )
    assert (min_y - margin) <= cy <= (max_y + margin), (
        f"Element center_y={cy:.3f} outside expected vertical range [{min_y - margin:.3f}, {max_y + margin:.3f}] "
        f"for region '{region}' (box: top={box.top:.3f}, bottom={box.bottom:.3f})"
    )


def assert_element_centered_horizontally(
    box: BoundingBox,
    min_left: float = 0.20,
    max_left: float = 0.35,
    min_right: float = 0.65,
    max_right: float = 0.80,
) -> None:
    """Verify that an element (like a modal command palette) is horizontally centered within criteria."""
    assert min_left <= box.left <= max_left, (
        f"Box left edge {box.left:.3f} outside expected centered span [{min_left}, {max_left}]"
    )
    assert min_right <= box.right <= max_right, (
        f"Box right edge {box.right:.3f} outside expected centered span [{min_right}, {max_right}]"
    )


def assert_active_tab(choice_result: Union[ChoiceResult, str], expected: str) -> None:
    """Assert active tab matches expected selection without fragile ANSI/pixel checks."""
    actual = choice_result.choice if isinstance(choice_result, ChoiceResult) else choice_result
    assert actual == expected, (
        f"Active tab mismatch: expected '{expected}', got '{actual}' "
        f"(confidence: {getattr(choice_result, 'confidence', 'N/A')})"
    )


def assert_modal_state(noul_result: Union[NoulResult, float, bool], expected_visible: bool) -> None:
    """Assert modal dialog presence/absence using calibrated Noul probability thresholds."""
    if isinstance(noul_result, bool):
        prob = 1.0 if noul_result else 0.0
    elif isinstance(noul_result, NoulResult):
        prob = noul_result.probability
    else:
        prob = float(noul_result)

    if expected_visible:
        assert prob >= 0.70, (
            f"Expected modal to be visible (prob >= 0.70), but Jev reported probability={prob:.3f}"
        )
    else:
        assert prob <= 0.30, (
            f"Expected modal to be hidden (prob <= 0.30), but Jev reported probability={prob:.3f}"
        )
