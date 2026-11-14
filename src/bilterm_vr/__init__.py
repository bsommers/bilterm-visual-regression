"""Bilterm Semantic Visual Regression Testing using TypeSafe Jev System One."""

from .models import (
    BoundingBox,
    ChoiceResult,
    NoulResult,
    VisualInspectionResult,
)
from .client import TypeSafeClient, MockTypeSafeClient
from .runner import VisualRegressionRunner
from .assertions import (
    assert_element_in_region,
    assert_active_tab,
    assert_modal_state,
    assert_element_docked,
    assert_choice,
    assert_noul_state,
    assert_element_centered_horizontally,
    Region,
)

__all__ = [
    "BoundingBox",
    "ChoiceResult",
    "NoulResult",
    "VisualInspectionResult",
    "TypeSafeClient",
    "MockTypeSafeClient",
    "VisualRegressionRunner",
    "assert_element_in_region",
    "assert_active_tab",
    "assert_modal_state",
    "assert_element_docked",
    "assert_choice",
    "assert_noul_state",
    "assert_element_centered_horizontally",
    "Region",
]
