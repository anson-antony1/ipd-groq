"""Iterated Prisoner's Dilemma tournament over HTTP-served LLM players.

Two properties this harness is built around:

1. A run is repeatable. Every request carries a seed derived deterministically
   from (base_seed, match, round, player), and the player service pins
   temperature=0. Re-running with the same --seed issues identical requests.
2. A failed API call is never scored. If a player cannot produce a legal move
   after --max-retries attempts, the round is discarded and the match is marked
   aborted. Recording a rate-limit or timeout as a "defect" would put
   fabricated strategy data into the results.
"""

import argparse
import json
import logging
import time
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

PAYOFF_MATRIX = {
    ("cooperate", "cooperate"): (3, 3),   # R
    ("cooperate", "defect"): (0, 5),      # S, T
    ("defect", "cooperate"): (5, 0),      # T, S
    ("defect", "defect"): (1, 1),         # P
}

log = logging.getLogger("ipd")


def configure_logging(out_dir: Path, verbose: bool = True) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    handlers: List[logging.Handler] = [
        logging.FileHandler(out_dir / "tournament.log", mode="w")
    ]
    if verbose:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        handlers=handlers,
        force=True,
    )


class TournamentEngine:
    def __init__(
        self,
        players: List[Dict],
        rounds_per_match: int = 10,
        base_seed: int = 42,
        max_retries: int = 3,
        pause: float = 0.5,
        out_dir: Path = Path("results"),
    ):
        self.players = players
        self.rounds_per_match = rounds_per_match
        self.base_seed = base_seed
        self.max_retries = max_retries
        self.pause = pause
        self.out_dir = out_dir
        self.scores = {p["name"]: 0 for p in players}
        self.rounds: List[Dict] = []
        self.matches: List[Dict] = []
        self.failed_calls = 0

    def seed_for(self, match_idx: int, round_num: int, player_idx: int) -> int:
        """Deterministic per-request seed, stable across runs for a given base."""
        return (
            self.base_seed * 1_000_003
            + match_idx * 10_007
            + round_num * 101
            + player_idx
        )

    def get_move(self, url: str, payload: Dict) -> Tuple[Optional[str], Optional[str]]:
        """Return (move, error). Retries transient failures with backoff."""
        last_error = "no attempt made"
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = requests.post(f"{url}/make_move", json=payload, timeout=15)
                resp.raise_for_status()
                body = resp.json()
            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"
            else:
                if body.get("ok") and body.get("move") in ("cooperate", "defect"):
                    return body["move"], None
                last_error = body.get("error") or f"malformed response: {body!r}"

            self.failed_calls += 1
            log.warning("  %s attempt %d/%d failed: %s",
                        url, attempt, self.max_retries, last_error)
            if attempt < self.max_retries:
                time.sleep(self.pause * (2 ** (attempt - 1)))
        return None, last_error

    def play_match(self, match_idx: int, player_a: Dict, player_b: Dict) -> Dict:
        history_a: List[Dict] = []
        history_b: List[Dict] = []
        score_a = score_b = 0
        aborted_reason = None
        completed = 0

        log.info("=" * 60)
        log.info("Match %d: %s vs %s", match_idx, player_a["name"], player_b["name"])
        log.info("=" * 60)

        for round_num in range(1, self.rounds_per_match + 1):
            move_a, err_a = self.get_move(player_a["url"], {
                "opponent_id": player_b["name"],
                "history": history_a,
                "seed": self.seed_for(match_idx, round_num, 0),
            })
            move_b, err_b = self.get_move(player_b["url"], {
                "opponent_id": player_a["name"],
                "history": history_b,
                "seed": self.seed_for(match_idx, round_num, 1),
            })

            if move_a is None or move_b is None:
                # Discard the round rather than inventing a move for it.
                aborted_reason = (
                    f"round {round_num}: {player_a['name']}={err_a or 'ok'}, "
                    f"{player_b['name']}={err_b or 'ok'}"
                )
                log.error("  ABORTING match — %s", aborted_reason)
                break

            payoff_a, payoff_b = PAYOFF_MATRIX[(move_a, move_b)]
            score_a += payoff_a
            score_b += payoff_b
            completed = round_num

            log.info(
                "  Round %2d: %s=%s (+%d)  |  %s=%s (+%d)  |  running %d-%d",
                round_num, player_a["name"], move_a.upper(), payoff_a,
                player_b["name"], move_b.upper(), payoff_b, score_a, score_b,
            )

            self.rounds.append({
                "match": match_idx,
                "round": round_num,
                "player_a": player_a["name"], "move_a": move_a, "payoff_a": payoff_a,
                "player_b": player_b["name"], "move_b": move_b, "payoff_b": payoff_b,
                "cum_a": score_a, "cum_b": score_b,
            })
            history_a.append({"round": round_num, "my_move": move_a, "opponent_move": move_b})
            history_b.append({"round": round_num, "my_move": move_b, "opponent_move": move_a})
            time.sleep(self.pause)

        # Only completed rounds contribute to the tournament table.
        self.scores[player_a["name"]] += score_a
        self.scores[player_b["name"]] += score_b

        status = "ABORTED" if aborted_reason else "complete"
        log.info("Match %d %s (%d/%d rounds): %d-%d",
                 match_idx, status, completed, self.rounds_per_match, score_a, score_b)

        return {
            "match": match_idx,
            "player_a": player_a["name"], "player_b": player_b["name"],
            "score_a": score_a, "score_b": score_b,
            "rounds_completed": completed,
            "rounds_requested": self.rounds_per_match,
            "aborted": aborted_reason is not None,
            "aborted_reason": aborted_reason,
        }

    def run_tournament(self) -> Dict:
        started = datetime.now(timezone.utc).isoformat()
        for match_idx, (a, b) in enumerate(combinations(self.players, 2)):
            self.matches.append(self.play_match(match_idx, a, b))

        summary = {
            "started_utc": started,
            "finished_utc": datetime.now(timezone.utc).isoformat(),
            "base_seed": self.base_seed,
            "rounds_per_match": self.rounds_per_match,
            "max_retries": self.max_retries,
            "players": self.players,
            "scores": self.scores,
            "matches": self.matches,
            "failed_calls": self.failed_calls,
            "aborted_matches": sum(1 for m in self.matches if m["aborted"]),
        }

        log.info("#" * 60)
        log.info("FINAL SCORES (completed rounds only)")
        for name, score in sorted(self.scores.items(), key=lambda kv: kv[1], reverse=True):
            log.info("  %-34s : %d", name, score)
        if summary["aborted_matches"]:
            log.warning("%d match(es) aborted, %d failed API call(s) — results are partial",
                        summary["aborted_matches"], self.failed_calls)
        log.info("#" * 60)
        return summary

    def write_results(self, summary: Dict) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        (self.out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        with (self.out_dir / "rounds.jsonl").open("w") as f:
            for r in self.rounds:
                f.write(json.dumps(r) + "\n")
        log.info("Wrote %s and %s",
                 self.out_dir / "summary.json", self.out_dir / "rounds.jsonl")


def main() -> None:
    p = argparse.ArgumentParser(
        description="Run an IPD tournament between HTTP-served LLM players."
    )
    p.add_argument("--rounds", type=int, default=10, help="rounds per match (default 10)")
    p.add_argument("--seed", type=int, default=42, help="base seed; same seed = same requests")
    p.add_argument("--max-retries", type=int, default=3, help="attempts per move before aborting")
    p.add_argument("--pause", type=float, default=0.5, help="seconds between calls")
    p.add_argument("--out", type=Path, default=Path("results"), help="output directory")
    p.add_argument("--quiet", action="store_true", help="log to file only")
    args = p.parse_args()

    configure_logging(args.out, verbose=not args.quiet)

    players = [
        {"name": "Llama 3.1 8B (Groq)", "url": "http://localhost:8041"},
        {"name": "Llama 3.3 70B (Groq)", "url": "http://localhost:8042"},
    ]

    engine = TournamentEngine(
        players,
        rounds_per_match=args.rounds,
        base_seed=args.seed,
        max_retries=args.max_retries,
        pause=args.pause,
        out_dir=args.out,
    )
    summary = engine.run_tournament()
    engine.write_results(summary)


if __name__ == "__main__":
    main()
