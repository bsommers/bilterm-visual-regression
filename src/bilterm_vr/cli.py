"""Command line interface for running visual regression inspections on PNG buffers."""

import argparse
import sys
import json
from pathlib import Path
from .runner import VisualRegressionRunner, DEFAULT_TERMINAL_QUESTIONS
from .models import VisualInspectionResult


def main() -> None:
    parser = argparse.ArgumentParser(
        description="bilterm-vr: Semantic visual regression CLI using TypeSafe Jev"
    )
    parser.add_argument("image", help="Path to terminal screenshot PNG")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Force offline mock mode instead of live API",
    )
    parser.add_argument(
        "--fixtures-dir",
        default="fixtures",
        help="Directory containing fixture JSON responses",
    )
    parser.add_argument(
        "--verify-modal",
        action="store_true",
        help="Assert modal dialog is visible and centered",
    )
    parser.add_argument(
        "--verify-tab",
        choices=["terminal", "mcp_console", "settings"],
        help="Assert expected active tab",
    )
    parser.add_argument(
        "--verify-theme",
        choices=["tron", "classic", "dark", "light"],
        help="Assert expected theme",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON results",
    )

    args = parser.parse_args()
    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Error: Image file not found: {image_path}", file=sys.stderr)
        sys.exit(1)

    runner = VisualRegressionRunner(
        use_mock=args.mock,
        fixtures_dir=args.fixtures_dir,
    )

    try:
        if args.verify_modal:
            result = runner.verify_modal_dialog_centered(image_path, expected_visible=True)
            print("✓ Modal dialog verified: centered within tolerance.")
        elif args.verify_tab or args.verify_theme:
            result = runner.verify_active_tab_and_theme(
                image_path,
                expected_tab=args.verify_tab or "terminal",
                expected_theme=args.verify_theme,
            )
            print(f"✓ Tab/Theme verified: tab={args.verify_tab}, theme={args.verify_theme}")
        else:
            result = runner.run_check(image_path)
            print(f"=== Visual Inspection for {image_path.name} ===")
            for name, box in result.boxes.items():
                print(
                    f"  Box '{name}': top={box.top:.3f}, left={box.left:.3f}, "
                    f"bottom={box.bottom:.3f}, right={box.right:.3f}"
                )
            for name, choice in result.choices.items():
                print(f"  Choice '{name}': {choice.choice} (conf: {choice.confidence:.2f})")
            for name, noul in result.nouls.items():
                print(f"  Noul '{name}': prob={noul.probability:.3f} (is_true={noul.is_true})")

        if args.json:
            print(json.dumps(result.raw_response, indent=2))

    except AssertionError as e:
        print(f"❌ Visual Regression Assertion Failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Execution Error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
