"""Run the curated frames against live Jev, save raw responses, compare with expected answers.

    set -a; . ~/.env; set +a            # exports TYPESAFE_API_KEY
    TYPESAFE_ENDPOINT=/v1/ask python3 scripts/live_check.py [--runs N]

Never prints the key. Raw responses go to fixtures/live/<frame>.run<N>.json.
"""
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import httpx
from bilterm_vr.client import TypeSafeClient
from bilterm_vr.runner import DEFAULT_TERMINAL_QUESTIONS as Q

ap = argparse.ArgumentParser()
ap.add_argument("--runs", type=int, default=1)
ap.add_argument("--only", help="substring filter on frame name")
a = ap.parse_args()

client = TypeSafeClient()
out_dir = ROOT / "fixtures" / "live"
out_dir.mkdir(exist_ok=True)
frames = sorted(p for p in (ROOT / "fixtures" / "real").glob("*.png") if not a.only or a.only in p.stem)
ok = total = 0
for png in frames:
    exp = json.loads(png.with_suffix(".json").read_text())["answers"]
    for run in range(1, a.runs + 1):
        try:
            res = client.inspect_frame(png, Q)
        except httpx.HTTPStatusError as e:
            print(f"{png.stem}: HTTP {e.response.status_code} {e.response.text[:300]!r}")
            print(f"endpoint={client.endpoint}")
            sys.exit(2)
        except Exception as e:
            print(f"{png.stem}: {type(e).__name__}: {str(e)[:300]}")
            sys.exit(2)
        (out_dir / f"{png.stem}.run{run}.json").write_text(json.dumps(res.raw_response, indent=2) + "\n")
        row = []
        for k in ("layout", "theme", "style"):
            got = res.get_choice(k).choice
            good = got == exp[k]["choice"]
            ok += good; total += 1
            row.append(f"{k}={got}{'' if good else '(want ' + exp[k]['choice'] + ')'}")
        p = res.get_noul("drawer_visible").probability
        good = (p >= 0.7) == (exp["drawer_visible"]["probability"] >= 0.7) and not res.get_noul("drawer_visible").is_uncertain
        ok += good; total += 1
        row.append(f"drawer_p={p:.2f}{'' if good else ' WRONG'}")
        sd = res.get_box("session_drawer"); sb = res.get_box("status_bar")
        row.append(f"drawer_box=({sd.left:.2f},{sd.right:.2f}) status_top={sb.top:.2f}")
        print(f"{png.stem} run{run}: " + "  ".join(row))
print(f"\nclassification accuracy: {ok}/{total}")
