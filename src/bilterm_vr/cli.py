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
        default="fixtures/real",
        help="Directory containing fixture JSON responses",
    )
    parser.add_argument("--verify-drawer", choices=["visible", "hidden"], help="Assert sessions drawer state")
    parser.add_argument("--verify-status-bar", action="store_true", help="Assert status bar is docked at the bottom")
    parser.add_argument("--verify-layout", choices=["single_pane", "side_by_side", "stacked"])
    parser.add_argument("--verify-theme", choices=["nord", "tron_grid"])
    parser.add_argument("--verify-style", choices=["classic", "modern"])
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
        checks = []
        if args.verify_drawer:
            result = runner.verify_drawer(image_path, args.verify_drawer == "visible")
            checks.append(f"drawer={args.verify_drawer}")
        if args.verify_status_bar:
            result = runner.verify_status_bar(image_path)
            checks.append("status_bar=docked")
        if args.verify_layout or args.verify_theme or args.verify_style:
            result = runner.verify_appearance(
                image_path, args.verify_layout, args.verify_theme, args.verify_style
            )
            checks.append(
                ", ".join(
                    f"{k}={v}"
                    for k, v in (("layout", args.verify_layout), ("theme", args.verify_theme), ("style", args.verify_style))
                    if v
                )
            )
        if checks:
            print("✓ Verified: " + "; ".join(checks))
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
