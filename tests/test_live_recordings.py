"""Replay *recorded live Jev responses* (fixtures/live/*.run*.json) through the harness.

Unlike fixtures/real/*.json (idealised expected answers), these are real model output, 8 frames x 3 runs.
The thresholds below pin what was MEASURED, so a change in client, questions or assertions that alters
live behaviour shows up here. Re-record with scripts/live_check.py, then update the pins deliberately.
"""
import json
from pathlib import Path

import pytest

from bilterm_vr.client import MockTypeSafeClient
from bilterm_vr.runner import VisualRegressionRunner, DEFAULT_TERMINAL_QUESTIONS as Q

ROOT = Path(__file__).parent.parent / "fixtures"
MANIFEST = json.loads((ROOT / "real" / "manifest.json").read_text())["frames"]
RUNS = sorted((ROOT / "live").glob("*.run*.json"))

pytestmark = pytest.mark.skipif(not RUNS, reason="no recorded live responses")


def runner_for(rec: Path):
    stem = rec.name.rsplit(".run", 1)[0]
    client = MockTypeSafeClient()
    client.register_fixture(stem, json.loads(rec.read_text()))
    return stem, VisualRegressionRunner(client=client), ROOT / "real" / f"{stem}.png"


def test_recordings_cover_every_frame_three_times():
    assert len(RUNS) == 3 * len(MANIFEST)


@pytest.mark.parametrize("rec", RUNS, ids=lambda p: p.stem)
def test_layout_style_and_drawer_always_correct(rec):
    stem, r, png = runner_for(rec)
    t = MANIFEST[stem]
    r.verify_appearance(png, layout=t["layout"], style=t["style"])
    r.verify_drawer(png, expected_visible=t["drawer_visible"])


def _accuracy(question, only_theme=None):
    hit = tot = 0
    for rec in RUNS:
        stem, r, png = runner_for(rec)
        t = MANIFEST[stem]
        if only_theme and t["theme"] != only_theme:
            continue
        hit += r.run_check(png, {question: Q[question]}).get_choice(question).choice == t[question]
        tot += 1
    return hit, tot


def test_theme_is_reliable_on_tron_grid_only():
    """KNOWN LIMITATION: the model reads most nord frames as tron_grid. Measured 4/15 on nord, 9/9 on tron_grid."""
    assert _accuracy("theme", "tron_grid") == (9, 9)
    hit, tot = _accuracy("theme", "nord")
    assert tot == 15 and hit == 4, f"nord theme accuracy changed: {hit}/{tot}; update docs/REPORT.md if intended"


def test_status_bar_box_mostly_passes():
    """KNOWN FLAKE: modern__tron-grid__split sometimes boxes the bar around y=0.47 (2 of 24 runs fail)."""
    failed = []
    for rec in RUNS:
        _, r, png = runner_for(rec)
        try:
            r.verify_status_bar(png)
        except AssertionError:
            failed.append(rec.name)
    assert len(failed) == 2 and all(n.startswith("modern__tron-grid__split") for n in failed), failed
