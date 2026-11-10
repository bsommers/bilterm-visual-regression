"""Data structures and representations for TypeSafe responses and bounding primitives."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class BoundingBox:
    """Normalized bounding box coordinates (0.0 to 1.0).

    Attributes:
        top: normalized top edge coordinate (y min)
        left: normalized left edge coordinate (x min)
        bottom: normalized bottom edge coordinate (y max)
        right: normalized right edge coordinate (x max)
    """
    top: float
    left: float
    bottom: float
    right: float

    @property
    def width(self) -> float:
        return max(0.0, self.right - self.left)

    @property
    def height(self) -> float:
        return max(0.0, self.bottom - self.top)

    @property
    def center_x(self) -> float:
        return (self.left + self.right) / 2.0

    @property
    def center_y(self) -> float:
        return (self.top + self.bottom) / 2.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BoundingBox:
        # Handles TypeSafe box payload structure:
        # {"top": ..., "left": ..., "bottom": ..., "right": ...} or nested under "box"
        box_data = data.get("box", data)
        return cls(
            top=float(box_data.get("top", 0.0)),
            left=float(box_data.get("left", 0.0)),
            bottom=float(box_data.get("bottom", 0.0)),
            right=float(box_data.get("right", 0.0)),
        )

    def to_dict(self) -> Dict[str, float]:
        return {
            "top": round(self.top, 4),
            "left": round(self.left, 4),
            "bottom": round(self.bottom, 4),
            "right": round(self.right, 4),
        }


@dataclass
class ChoiceResult:
    """Result for a TypeSafe Choice primitive."""
    choice: str
    confidence: float = 1.0
    probabilities: Dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ChoiceResult:
        return cls(
            choice=data.get("choice", data.get("value", "")),
            confidence=float(data.get("confidence", 1.0)),
            probabilities=data.get("probabilities", {}),
        )


@dataclass
class NoulResult:
    """Result for a TypeSafe Noul primitive (probabilistic assertion)."""
    probability: float
    confidence: float = 1.0

    @property
    def is_true(self) -> bool:
        # Canonical TypeSafe default threshold: >= 0.70
        return self.probability >= 0.70

    @property
    def is_false(self) -> bool:
        # Canonical TypeSafe default threshold: <= 0.30
        return self.probability <= 0.30

    @property
    def is_uncertain(self) -> bool:
        return 0.30 < self.probability < 0.70

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> NoulResult:
        prob = data.get("probability", data.get("noul", 0.5))
        return cls(
            probability=float(prob),
            confidence=float(data.get("confidence", 1.0)),
        )


@dataclass
class VisualInspectionResult:
    """Aggregated inspection report for a terminal frame."""
    frame_name: str
    boxes: Dict[str, BoundingBox] = field(default_factory=dict)
    choices: Dict[str, ChoiceResult] = field(default_factory=dict)
    nouls: Dict[str, NoulResult] = field(default_factory=dict)
    raw_response: Dict[str, Any] = field(default_factory=dict)

    def get_box(self, name: str) -> Optional[BoundingBox]:
        return self.boxes.get(name)

    def get_choice(self, name: str) -> Optional[ChoiceResult]:
        return self.choices.get(name)

    def get_noul(self, name: str) -> Optional[NoulResult]:
        return self.nouls.get(name)
