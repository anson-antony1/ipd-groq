# Iterated Prisoner's Dilemma — two Llama models via Groq

A tournament harness that makes two Llama models play the Iterated Prisoner's
Dilemma against each other. Each model is served as its own FastAPI process, and
a separate engine drives the match, so a player sees nothing except the round
history it is handed.

I built this for a GatorAI session on game-theoretic behaviour in language
models. The question it is set up to answer is narrow: given only the history of
a repeated game and no strategy advice, does a model cooperate, defect, or
retaliate — and does model size change that?

## The game

Standard Prisoner's Dilemma payoffs, defined in `tournament_engine.py`:

| | opponent cooperates | opponent defects |
|---|---|---|
| **you cooperate** | 3 / 3 (R) | 0 / 5 (S / T) |
| **you defect** | 5 / 0 (T / S) | 1 / 1 (P) |

This satisfies both conditions that make it a real dilemma: `T > R > P > S`
(5 > 3 > 1 > 0) and `2R > T + S` (6 > 5), so mutual cooperation beats alternating
exploitation. Matches are round-robin over every pair of players, 10 rounds each
by default.

## How a player works

`llama_player_factory_groq.py` builds one FastAPI app per model, exposing
`POST /make_move` and `GET /health`. Each turn it sends:

- a fixed system prompt constraining the reply to exactly `cooperate` or `defect`
- the round history, serialised as `Round N: you=<move>, opp=<move>`

No strategy is suggested and nothing about the opponent is revealed beyond its
moves. There is no chain-of-thought or opponent-modelling prompt — the model gets
history and a move contract, nothing else.

A reply naming both moves or neither is treated as a failure rather than being
rounded to one of them, so an ambiguous answer never becomes invented data.

## What makes a run repeatable

1. **Pinned sampling.** The player service sets `temperature=0` on every call.
2. **Deterministic seeds.** The engine derives a seed from
   `(base_seed, match, round, player)` and sends it with each request, so
   `--seed 42` issues the same sequence of requests every time. Change `--seed`
   for an independent run.
3. **Real logging.** `logging` is configured with a file handler
   (`results/tournament.log`) and a console handler. Every round is appended to
   `results/rounds.jsonl`, and `results/summary.json` records the seed, round
   count, per-match scores, and failure counts. Runs are diffable.

**Failed calls are never scored.** If a model cannot produce a legal move after
`--max-retries` attempts, the round is discarded and the match is recorded as
`aborted` with the reason. An earlier version returned `defect` on any exception,
which made a rate-limit indistinguishable from a deliberate defection and quietly
corrupted the results. Only completed rounds contribute to the score table, and
the summary reports how many calls failed.

## Running it

```bash
git clone https://github.com/anson-antony1/ipd-groq.git
cd ipd-groq
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Add a Groq API key — get one at <https://console.groq.com/keys>:

```bash
echo 'GROQ_API_KEY=gsk_your_key_here' > .env
```

Start both player servers (terminal A):

```bash
python groq_runner.py
```

Run the tournament (terminal B):

```bash
python tournament_engine.py --rounds 10 --seed 42
```

Plot cumulative scores:

```bash
python plot_results.py
```

Model ids come from the environment, so a retired model can be swapped without
editing code:

```bash
IPD_MODEL_B=llama-3.1-8b-instant python groq_runner.py
```

Defaults are `llama-3.1-8b-instant` and `llama-3.3-70b-versatile`. Groq retires
models periodically — check <https://console.groq.com/docs/models> if a run fails
with a bad-model error.

## Results

**This repo ships no results.** Everything under `results/` is produced by a run
and is gitignored, so nothing stale or hand-written can end up here. A previous
version committed a `results.png` drawn from arrays typed into `plot_results.py`
rather than from measured data; that file and its `results.txt` have been
deleted, and `plot_results.py` now refuses to draw anything when
`results/rounds.jsonl` is missing.

A run produces `summary.json` (seed, scores, aborted matches, failed-call count),
`rounds.jsonl` (one record per round with both moves, both payoffs, and running
totals), `tournament.log`, and `results.png`.

## Files

| File | What it does |
|---|---|
| `llama_player_factory_groq.py` | FastAPI player factory: prompt construction, seeded Groq call, strict move parsing |
| `tournament_engine.py` | Payoffs, round-robin scheduling, retries, abort-on-failure, JSON/JSONL/log output |
| `groq_runner.py` | Launches one server per model on its own port |
| `plot_results.py` | Plots cumulative score per round from `rounds.jsonl` |

## Licence

MIT — see [LICENSE](LICENSE).
