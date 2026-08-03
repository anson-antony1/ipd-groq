"""Plot cumulative score per round from a real tournament run.

Reads results/rounds.jsonl written by tournament_engine.py. Nothing here is
hardcoded — if you have not run a tournament yet, this exits with a message
rather than drawing a chart from invented numbers.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # render without a display; savefig still works
import matplotlib.pyplot as plt  # noqa: E402


def load_rounds(path: Path):
    if not path.exists():
        raise SystemExit(
            f"{path} not found — run `python tournament_engine.py` first.\n"
            "This script only plots measured results; it has no fallback data."
        )
    with path.open() as f:
        rounds = [json.loads(line) for line in f if line.strip()]
    if not rounds:
        raise SystemExit(f"{path} is empty — no completed rounds to plot.")
    return rounds


def main() -> None:
    p = argparse.ArgumentParser(description="Plot cumulative IPD scores from a run.")
    p.add_argument("--rounds-file", type=Path, default=Path("results/rounds.jsonl"))
    p.add_argument("--match", type=int, default=None, help="match index (default: first)")
    p.add_argument("--out", type=Path, default=Path("results/results.png"))
    args = p.parse_args()

    rounds = load_rounds(args.rounds_file)
    match_idx = args.match if args.match is not None else min(r["match"] for r in rounds)
    match_rounds = sorted(
        (r for r in rounds if r["match"] == match_idx), key=lambda r: r["round"]
    )
    if not match_rounds:
        raise SystemExit(f"no rounds recorded for match {match_idx}")

    series = defaultdict(list)
    xs = [r["round"] for r in match_rounds]
    name_a = match_rounds[0]["player_a"]
    name_b = match_rounds[0]["player_b"]
    for r in match_rounds:
        series[name_a].append(r["cum_a"])
        series[name_b].append(r["cum_b"])

    for marker, (name, ys) in zip("os^dv", series.items()):
        plt.plot(xs, ys, label=name, marker=marker)

    plt.xlabel("Round")
    plt.ylabel("Cumulative score")
    plt.title(f"IPD Tournament — match {match_idx} ({len(xs)} rounds)")
    plt.legend()
    plt.grid(True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(args.out, dpi=150, bbox_inches="tight")
    print(f"wrote {args.out} from {len(match_rounds)} measured rounds")


if __name__ == "__main__":
    main()
