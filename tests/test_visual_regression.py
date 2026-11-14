"""Unit and integration tests for bilterm visual regression runner and assertions."""

import json
import pytest
from pathlib import Path
from bilterm_vr.models import BoundingBox, ChoiceResult, NoulResult
from bilterm_vr.assertions import (
    assert_element_in_region,
    assert_element_centered_horizontally,
    assert_element_docked,
    assert_active_tab,
    assert_modal_state,
    assert_choice,
    assert_noul_state,
    Region,
)
from bilterm_vr.client import MockTypeSafeClient
from bilterm_vr.runner import VisualRegressionRunner, DEFAULT_TERMINAL_QUESTIONS


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "real"


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
        box = BoundingBox(top=0.28, left=0.26, bottom=0.52, right=0.74)
        assert_element_centered_horizontally(box)
        assert_element_in_region(box, Region.CENTER)

    def test_centered_element_fails_if_skewed(self):
        with pytest.raises(AssertionError):
            assert_element_centered_horizontally(BoundingBox(top=0.1, left=0.05, bottom=0.4, right=0.45))

    def test_active_tab_assertion(self):
        assert_active_tab(ChoiceResult(choice="terminal"), "terminal")
        with pytest.raises(AssertionError):
            assert_active_tab(ChoiceResult(choice="terminal"), "settings")

    def test_modal_state_assertion(self):
        assert_modal_state(NoulResult(probability=0.94), expected_visible=True)
        assert_modal_state(NoulResult(probability=0.05), expected_visible=False)
        with pytest.raises(AssertionError):
            assert_modal_state(NoulResult(probability=0.94), expected_visible=False)

    def test_noul_state_accepts_bool_float_and_result(self):
        assert_noul_state(True, True)
        assert_noul_state(0.1, False, "drawer")
        with pytest.raises(AssertionError, match="drawer"):
            assert_noul_state(NoulResult(0.5), True, "drawer")  # uncertain is neither true nor false

    def test_choice_assertion(self):
        assert_choice(ChoiceResult(choice="nord"), "nord", "theme")
        assert_choice("nord", "nord")
        with pytest.raises(AssertionError, match="theme mismatch"):
            assert_choice(ChoiceResult(choice="nord"), "tron_grid", "theme")

    @pytest.mark.parametrize(
        "edge,box",
        [
            ("left", BoundingBox(0.0, 0.0, 1.0, 0.31)),
            ("right", BoundingBox(0.0, 0.7, 1.0, 1.0)),
            ("top", BoundingBox(0.0, 0.0, 0.1, 1.0)),
            ("bottom", BoundingBox(0.97, 0.0, 1.0, 1.0)),
        ],
    )
    def test_docked_passes(self, edge, box):
        assert_element_docked(box, edge, max_extent=0.45)

    def test_docked_fails_when_floating_or_too_large(self):
        with pytest.raises(AssertionError, match="not docked"):
            assert_element_docked(BoundingBox(0.0, 0.2, 1.0, 0.5), "left", 0.45)
        with pytest.raises(AssertionError, match="extent"):
            assert_element_docked(BoundingBox(0.0, 0.0, 1.0, 0.9), "left", 0.45)
        with pytest.raises(AssertionError, match="extent"):  # empty box = absent element
            assert_element_docked(BoundingBox(0.0, 0.0, 0.0, 0.0), "left", 0.45)
        with pytest.raises(ValueError):
            assert_element_docked(BoundingBox(0, 0, 1, 1), "middle", 0.5)


MANIFEST = json.loads((FIXTURES_DIR / "manifest.json").read_text())
FRAMES = MANIFEST["frames"]


@pytest.fixture(scope="module")
def runner():
    return VisualRegressionRunner(use_mock=True, fixtures_dir=FIXTURES_DIR)


def png(name: str) -> Path:
    return FIXTURES_DIR / f"{name}.png"


class TestRealFrames:
    """Mock-Jev checks over real bilterm frames, parametrised from the manifest ground truth."""

    @pytest.mark.parametrize("name", FRAMES)
    def test_appearance_matches_ground_truth(self, runner, name):
        t = FRAMES[name]
        runner.verify_appearance(png(name), layout=t["layout"], theme=t["theme"], style=t["style"])

    @pytest.mark.parametrize("name", FRAMES)
    def test_drawer_state_matches_ground_truth(self, runner, name):
        runner.verify_drawer(png(name), expected_visible=FRAMES[name]["drawer_visible"])

    @pytest.mark.parametrize("name", FRAMES)
    def test_status_bar_docked_at_bottom(self, runner, name):
        runner.verify_status_bar(png(name))

    def test_drawer_box_is_left_docked(self, runner):
        res = runner.verify_drawer(png("classic__nord__drawer"), expected_visible=True)
        box = res.get_box("session_drawer")
        assert box.left == pytest.approx(0.0, abs=0.03)
        assert 0.25 < box.right < 0.40


class TestNegativeCases:
    """The harness must fail loudly when a frame does not match the expectation."""

    def test_drawer_expected_but_absent(self, runner):
        with pytest.raises(AssertionError, match="sessions drawer"):
            runner.verify_drawer(png("classic__nord__split"), expected_visible=True)

    def test_drawer_unexpectedly_present(self, runner):
        with pytest.raises(AssertionError, match="sessions drawer"):
            runner.verify_drawer(png("classic__nord__drawer"), expected_visible=False)

    def test_wrong_theme(self, runner):
        with pytest.raises(AssertionError, match="theme mismatch"):
            runner.verify_appearance(png("classic__nord__single"), theme="tron_grid")

    def test_wrong_style(self, runner):
        with pytest.raises(AssertionError, match="style mismatch"):
            runner.verify_appearance(png("modern__nord__split"), style="classic")

    def test_wrong_layout(self, runner):
        with pytest.raises(AssertionError, match="layout mismatch"):
            runner.verify_appearance(png("classic__nord__single"), layout="side_by_side")

    def test_appearance_requires_an_expectation(self, runner):
        with pytest.raises(ValueError):
            runner.verify_appearance(png("classic__nord__single"))

    def test_misplaced_drawer_box_is_caught(self):
        client = MockTypeSafeClient()
        resp = json.loads((FIXTURES_DIR / "classic__nord__drawer.json").read_text())
        resp["answers"]["session_drawer"] = {"top": 0.0, "left": 0.55, "bottom": 1.0, "right": 0.95}
        client.register_fixture("classic__nord__drawer", resp)
        with pytest.raises(AssertionError):
            VisualRegressionRunner(client=client).verify_drawer(png("classic__nord__drawer"))


class TestFrameIntegrity:
    """Pixel-level checks (no model): the labels describe what is really in the PNGs."""

    @pytest.mark.parametrize("name", FRAMES)
    def test_png_matches_manifest(self, name):
        import hashlib
        from PIL import Image

        im = Image.open(png(name)).convert("RGB")
        assert list(im.size) == MANIFEST["frame_size"]
        assert hashlib.sha256(im.tobytes()).hexdigest() == FRAMES[name]["pixel_sha256"]
        assert len(im.getcolors(maxcolors=1_000_000)) > 10, "frame looks blank"

    def test_every_png_has_manifest_entry(self):
        assert {p.stem for p in FIXTURES_DIR.glob("*.png")} == set(FRAMES)

    def test_theme_labels_agree_with_pixels(self):
        from PIL import Image, ImageStat

        def brightness(name):
            return sum(ImageStat.Stat(Image.open(png(name)).convert("L")).mean)

        for style in ("classic", "modern"):
            nord = [n for n, t in FRAMES.items() if t["theme"] == "nord" and t["style"] == style]
            tron = [n for n, t in FRAMES.items() if t["theme"] == "tron_grid" and t["style"] == style]
            assert min(map(brightness, nord)) > max(map(brightness, tron))

    def test_drawer_labels_agree_with_pixels(self):
        from PIL import Image, ImageChops

        def left_strip(name):
            im = Image.open(png(name)).convert("RGB")
            return im.crop((0, 0, int(im.width * 0.28), im.height))

        # Same style+theme: the drawer frame's left strip differs from the plain split frame's.
        diff = ImageChops.difference(left_strip("classic__nord__drawer"), left_strip("classic__nord__split"))
        assert diff.getbbox() is not None


class TestCaptureRoundTrip:
    def test_convert_regenerates_fixtures(self, tmp_path):
        from PIL import Image
        from bilterm_vr.capture import convert
        from bilterm_vr.scenes import CURATED_FRAMES

        ppm_dir = tmp_path / "ppm"
        ppm_dir.mkdir()
        for n in CURATED_FRAMES:
            Image.open(png(n)).convert("RGB").save(ppm_dir / f"{n}.ppm")
        out = tmp_path / "out"
        manifest = convert(ppm_dir, out, bilterm_commit="deadbee")
        assert manifest["bilterm_commit"] == "deadbee"
        assert manifest["frames"] == {k: v for k, v in FRAMES.items()}
        for n in CURATED_FRAMES:
            assert json.loads((out / f"{n}.json").read_text()) == json.loads((FIXTURES_DIR / f"{n}.json").read_text())

    def test_missing_frame_is_an_error(self, tmp_path):
        from bilterm_vr.capture import convert

        with pytest.raises(FileNotFoundError):
            convert(tmp_path, tmp_path / "out")


class TestMockClientFallback:
    def test_unrecorded_frame_derives_from_name(self):
        res = MockTypeSafeClient().inspect_frame("modern__nord__drawer.png", DEFAULT_TERMINAL_QUESTIONS)
        assert res.get_noul("drawer_visible").is_true
        assert res.get_choice("style").choice == "modern"

    def test_unknown_name_is_an_error_not_a_guess(self):
        with pytest.raises(KeyError):
            MockTypeSafeClient().inspect_frame("whatever.png", DEFAULT_TERMINAL_QUESTIONS)


class TestLiveClientWireFormat:
    """Pins the request/response shapes to TypeSafe's published /v1/systemone schema (no network)."""

    def test_request_and_response_shapes(self, monkeypatch):
        import httpx
        from bilterm_vr.client import TypeSafeClient

        seen = {}

        def fake_post(self, url, json=None, headers=None):
            seen.update(url=url, json=json, headers=headers)
            return httpx.Response(
                200,
                request=httpx.Request("POST", url),
                json={
                    "model": "jev-latest",
                    "usage": {"input_tokens": 1, "output_tokens": 1},
                    "answers": {
                        "layout": {"type": "choice", "choice": "side_by_side", "confidence": 0.9,
                                   "probabilities": {"single_pane": 0.05, "side_by_side": 0.9, "stacked": 0.05}},
                        "drawer_visible": {"type": "noul", "noul": 0.97},
                        "session_drawer": {"type": "box", "confidence": None,
                                           "box": {"top": 0.0, "left": 0.0, "bottom": 1.0, "right": 0.3}},
                        "status_bar": {"type": "box", "confidence": 0.9,
                                       "box": {"top": 0.97, "left": 0.0, "bottom": 1.0, "right": 1.0}},
                    },
                },
            )

        monkeypatch.setattr(httpx.Client, "post", fake_post)
        client = TypeSafeClient(api_key="test-key")
        qs = {k: DEFAULT_TERMINAL_QUESTIONS[k] for k in ("layout", "drawer_visible", "session_drawer", "status_bar")}
        res = client.inspect_frame(png("classic__nord__drawer"), qs)

        assert seen["url"].endswith("/v1/systemone")
        assert seen["headers"]["TypeSafe-Danger-Zone-Images"] == "true"
        (placeholder, asset), = seen["json"]["assets"].items()
        assert seen["json"]["state"] == placeholder
        assert asset["type"] == "image" and asset["format"] == "png" and asset["data_base64"]
        for q in seen["json"]["questions"].values():
            assert q["type"] in {"box", "choice", "noul"}
            if q["type"] == "choice":
                assert q["criteria"] and "options" not in q
        assert res.get_choice("layout").choice == "side_by_side"
        assert res.get_noul("drawer_visible").probability == pytest.approx(0.97)
        assert res.get_box("session_drawer").right == pytest.approx(0.3)
