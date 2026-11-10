"""Client interfaces for TypeSafe Jev System One image queries."""

from __future__ import annotations
import os
import json
import base64
from typing import Dict, Any, Optional
from pathlib import Path
import httpx
from .models import (
    BoundingBox,
    ChoiceResult,
    NoulResult,
    VisualInspectionResult,
)


class BaseTypeSafeClient:
    """Abstract base client for TypeSafe API."""

    def inspect_frame(
        self,
        image_path: Path | str,
        questions: Dict[str, Any],
        model: str = "jev-latest",
    ) -> VisualInspectionResult:
        raise NotImplementedError


class TypeSafeClient(BaseTypeSafeClient):
    """Live HTTP client for TypeSafe System One API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.typesafe.ai",
        timeout: float = 30.0,
    ):
        self.api_key = api_key or os.environ.get("TYPESAFE_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "TypeSafe API key must be provided or set in TYPESAFE_API_KEY environment variable."
            )
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _encode_image(self, image_path: Path | str) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def inspect_frame(
        self,
        image_path: Path | str,
        questions: Dict[str, Any],
        model: str = "jev-latest",
    ) -> VisualInspectionResult:
        path = Path(image_path)
        frame_id = path.stem
        encoded_data = self._encode_image(path)

        payload = {
            "model": model,
            "state": {
                "terminal_frame": frame_id,
            },
            "assets": {
                frame_id: {
                    "type": "image",
                    "part": "screen_capture",
                    "data": f"data:image/png;base64,{encoded_data}",
                }
            },
            "questions": questions,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "TypeSafe-Danger-Zone-Images": "true",
        }

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                f"{self.base_url}/v1/ask",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        return self._parse_response(frame_id, data, questions)

    def _parse_response(
        self, frame_name: str, data: Dict[str, Any], questions: Dict[str, Any]
    ) -> VisualInspectionResult:
        answers = data.get("answers", data)
        boxes: Dict[str, BoundingBox] = {}
        choices: Dict[str, ChoiceResult] = {}
        nouls: Dict[str, NoulResult] = {}

        for q_name, q_spec in questions.items():
            ans = answers.get(q_name, {})
            q_type = q_spec.get("type")
            if q_type == "box":
                boxes[q_name] = BoundingBox.from_dict(ans)
            elif q_type == "choice":
                choices[q_name] = ChoiceResult.from_dict(ans)
            elif q_type == "noul":
                nouls[q_name] = NoulResult.from_dict(ans)

        return VisualInspectionResult(
            frame_name=frame_name,
            boxes=boxes,
            choices=choices,
            nouls=nouls,
            raw_response=data,
        )


class MockTypeSafeClient(BaseTypeSafeClient):
    """Offline mock client responding with deterministic recorded responses or heuristic fixtures."""

    def __init__(self, fixtures_map: Optional[Dict[str, Dict[str, Any]]] = None):
        self.fixtures_map = fixtures_map or {}

    def register_fixture(self, frame_name: str, response: Dict[str, Any]) -> None:
        self.fixtures_map[frame_name] = response

    def inspect_frame(
        self,
        image_path: Path | str,
        questions: Dict[str, Any],
        model: str = "jev-latest",
    ) -> VisualInspectionResult:
        path = Path(image_path)
        frame_name = path.stem

        if frame_name in self.fixtures_map:
            data = self.fixtures_map[frame_name]
        else:
            # Fallback heuristic responses based on standard frame names
            data = self._generate_heuristic_response(frame_name, questions)

        boxes: Dict[str, BoundingBox] = {}
        choices: Dict[str, ChoiceResult] = {}
        nouls: Dict[str, NoulResult] = {}

        for q_name, q_spec in questions.items():
            ans = data.get("answers", data).get(q_name, {})
            q_type = q_spec.get("type")
            if q_type == "box":
                boxes[q_name] = BoundingBox.from_dict(ans)
            elif q_type == "choice":
                choices[q_name] = ChoiceResult.from_dict(ans)
            elif q_type == "noul":
                nouls[q_name] = NoulResult.from_dict(ans)

        return VisualInspectionResult(
            frame_name=frame_name,
            boxes=boxes,
            choices=choices,
            nouls=nouls,
            raw_response=data,
        )

    def _generate_heuristic_response(
        self, frame_name: str, questions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a realistic mock response matching bilterm visual features."""
        answers: Dict[str, Any] = {}
        for q_name, q_spec in questions.items():
            q_type = q_spec.get("type")
            if q_type == "box":
                if "palette" in q_name or "command" in q_name or "modal" in q_name:
                    # Centered floating palette matching spec bounds:
                    # 0.20 < left < 0.35, 0.65 < right < 0.80
                    answers[q_name] = {
                        "top": 0.28,
                        "left": 0.26,
                        "bottom": 0.52,
                        "right": 0.74,
                    }
                elif "status" in q_name:
                    answers[q_name] = {
                        "top": 0.94,
                        "left": 0.0,
                        "bottom": 1.0,
                        "right": 1.0,
                    }
                elif "tab" in q_name or "header" in q_name:
                    answers[q_name] = {
                        "top": 0.0,
                        "left": 0.0,
                        "bottom": 0.08,
                        "right": 1.0,
                    }
                else:
                    answers[q_name] = {
                        "top": 0.1,
                        "left": 0.1,
                        "bottom": 0.9,
                        "right": 0.9,
                    }
            elif q_type == "choice":
                opts = q_spec.get("options", [])
                if "tab" in q_name:
                    if "settings" in frame_name:
                        choice = "settings"
                    elif "mcp" in frame_name:
                        choice = "mcp_console"
                    else:
                        choice = "terminal"
                elif "theme" in q_name:
                    if "tron" in frame_name:
                        choice = "tron"
                    elif "classic" in frame_name:
                        choice = "classic"
                    elif "light" in frame_name:
                        choice = "light"
                    else:
                        choice = "dark"
                elif "split" in q_name or "layout" in q_name:
                    if "split_v" in frame_name or "vertical" in frame_name:
                        choice = "vertical_split"
                    elif "split_h" in frame_name or "horizontal" in frame_name:
                        choice = "horizontal_split"
                    else:
                        choice = "single"
                else:
                    choice = opts[0] if opts else "default"

                answers[q_name] = {
                    "choice": choice,
                    "confidence": 0.96,
                    "probabilities": {opt: (0.96 if opt == choice else 0.02) for opt in opts},
                }
            elif q_type == "noul":
                if "modal" in q_name or "dialog" in q_name or "palette" in q_name:
                    is_visible = "modal" in frame_name or "palette" in frame_name
                    prob = 0.95 if is_visible else 0.04
                else:
                    prob = 0.92
                answers[q_name] = {
                    "probability": prob,
                    "confidence": 0.98,
                }
        return {"answers": answers}
