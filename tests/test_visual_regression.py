"""Unit and integration tests for bilterm visual regression runner and assertions."""

import pytest
from pathlib import Path
from bilterm_vr.models import BoundingBox, ChoiceResult, NoulResult
from bilterm_vr.assertions import (
    assert_element_in_region,
    assert_element_centered_horizontally,
    assert_active_tab,
    assert_modal_state,
    Region,
)
from bilterm_vr.client import MockTypeSafeClient
from bilterm_vr.runner import VisualRegressionRunner, DEFAULT_TERMINAL_QUESTIONS


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestModelsAndPrimitives:
    def test_bounding_box_calculations(self):
        box = BoundingBox(top=0.20, left=0.25, bottom=0.60, right=0.75)
        assert box.width == pytest.approx(0.50)
        assert box.height == pytest.approx(0.40)
        assert box.center_x == pytest.approx(0.50)
        assert box.center_y == pytest.approx(0.40)

        d = box.to_dict()
        assert d == {"top": 0.2, "left": 0.25, "bottom": 0.6, "right": 0.75}

    def test_noul_thresholds(self):
        noul_high = NoulResult(probability=0.85)
        assert noul_high.is_true is True
        assert noul_high.is_false is False
        assert noul_high.is_uncertain is False

        noul_low = NoulResult(probability=0.15)
        assert noul_low.is_true is False
        assert noul_low.is_false is True

        noul_mid = NoulResult(probability=0.52)
        assert noul_mid.is_true is False
        assert noul_mid.is_false is False
        assert noul_mid.is_uncertain is True

    def test_choice_result(self):
        choice = ChoiceResult(
            choice="settings",
            confidence=0.99,
            probabilities={"settings": 0.99, "terminal": 0.01},
        )
        assert choice.choice == "settings"
        assert choice.confidence == 0.99


class TestAssertions:
    def test_centered_element_passes(self):
        # Spec bounds: 0.20 < left < 0.35, 0.65 < right < 0.80
        box = BoundingBox(top=0.28, left=0.26, bottom=0.52, right=0.74)
        assert_element_centered_horizontally(box)
        assert_element_in_region(box, Region.CENTER)

    def test_centered_element_fails_if_skewed(self):
        skewed_box = BoundingBox(top=0.10, left=0.05, bottom=0.40, right=0.45)
        with pytest.raises(AssertionError):
            assert_element_centered_horizontally(skewed_box)

    def test_active_tab_assertion(self):
        choice = ChoiceResult(choice="terminal")
        assert_active_tab(choice, "terminal")

        with pytest.raises(AssertionError):
            assert_active_tab(choice, "settings")

    def test_modal_state_assertion(self):
        noul_visible = NoulResult(probability=0.94)
        noul_hidden = NoulResult(probability=0.05)

        assert_modal_state(noul_visible, expected_visible=True)
        assert_modal_state(noul_hidden, expected_visible=False)

        with pytest.raises(AssertionError):
            assert_modal_state(noul_visible, expected_visible=False)

        with pytest.raises(AssertionError):
            assert_modal_state(noul_hidden, expected_visible=True)


class TestVisualRegressionFixtures:
    @pytest.fixture
    def runner(self):
        return VisualRegressionRunner(use_mock=True, fixtures_dir=FIXTURES_DIR)

    def test_normal_terminal_frame(self, runner):
        img_path = FIXTURES_DIR / "terminal_normal.png"
        res = runner.run_check(img_path)

        assert res.get_choice("active_tab").choice == "terminal"
        assert res.get_choice("theme").choice == "dark"
        assert res.get_noul("modal_visible").is_false is True

    def test_command_palette_modal_verification(self, runner):
        img_path = FIXTURES_DIR / "terminal_modal_palette.png"
        res = runner.verify_modal_dialog_centered(img_path, expected_visible=True)

        assert res.get_noul("modal_visible").is_true is True
        box = res.get_box("command_palette")
        assert box is not None
        assert 0.20 < box.left < 0.35
        assert 0.65 < box.right < 0.80

    def test_settings_tab_switch(self, runner):
        img_path = FIXTURES_DIR / "terminal_settings_tab.png"
        res = runner.verify_active_tab_and_theme(img_path, expected_tab="settings")
        assert res.get_choice("active_tab").choice == "settings"

    def test_mcp_console_tab_switch(self, runner):
        img_path = FIXTURES_DIR / "terminal_mcp_tab.png"
        res = runner.verify_active_tab_and_theme(img_path, expected_tab="mcp_console")
        assert res.get_choice("active_tab").choice == "mcp_console"

    def test_tron_theme_classification(self, runner):
        img_path = FIXTURES_DIR / "terminal_tron_theme.png"
        res = runner.verify_active_tab_and_theme(
            img_path, expected_tab="terminal", expected_theme="tron"
        )
        assert res.get_choice("theme").choice == "tron"


class TestMockClientHeuristicFallback:
    def test_fallback_without_fixture_files(self):
        client = MockTypeSafeClient()
        # Querying an unrecorded frame path
        res = client.inspect_frame(
            "unknown_frame_modal.png",
            questions=DEFAULT_TERMINAL_QUESTIONS,
        )
        assert res.get_noul("modal_visible").is_true is True
        box = res.get_box("command_palette")
        assert box.center_x == pytest.approx(0.50)
