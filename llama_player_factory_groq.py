import os
from typing import Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from groq import Groq
from pydantic import BaseModel

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


class MoveRequest(BaseModel):
    opponent_id: str
    history: List[Dict]  # [{round, my_move, opponent_move}...]
    seed: Optional[int] = None


class MoveResponse(BaseModel):
    """A move, or an explicit failure.

    `move` is set only when the model actually produced a legal move. A None
    move with ok=False means the call failed or the reply was unparseable — the
    caller must not record that as a strategic choice.
    """

    move: Optional[str] = None
    ok: bool = True
    error: Optional[str] = None


SYSTEM_PROMPT = (
    "You are playing the Iterated Prisoner's Dilemma. "
    "On every turn you MUST reply with EXACTLY one lowercase word: "
    "'cooperate' or 'defect'. No punctuation. No explanations."
)


def _history_to_prompt(history: List[Dict]) -> str:
    if not history:
        return "Game start. Reply ONLY 'cooperate' or 'defect'."
    lines = [f"Round {h['round']}: you={h['my_move']}, opp={h['opponent_move']}."
             for h in history]
    return "History:\n" + "\n".join(lines) + "\nReply ONLY 'cooperate' or 'defect'."


def _parse_move(text: str) -> Optional[str]:
    """Return the move, or None if the reply names both moves or neither.

    Guessing on an ambiguous reply would invent data, so an unparseable answer
    is surfaced as a failure instead of being rounded to 'defect'.
    """
    said_cooperate = "cooperate" in text
    said_defect = "defect" in text
    if said_cooperate and not said_defect:
        return "cooperate"
    if said_defect and not said_cooperate:
        return "defect"
    return None


def create_app(model_id: str) -> FastAPI:
    app = FastAPI(title=f"Llama Player via Groq: {model_id}")

    @app.get("/health")
    async def health():
        return {"ok": True, "model": model_id}

    @app.post("/make_move", response_model=MoveResponse)
    async def make_move(request: MoveRequest):
        user_prompt = _history_to_prompt(request.history)
        # temperature=0 plus a caller-supplied seed is what makes a run
        # repeatable; without both, Groq resamples on every call.
        kwargs = {
            "model": model_id,
            "temperature": 0,
            "max_tokens": 4,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        }
        if request.seed is not None:
            kwargs["seed"] = request.seed

        try:
            resp = client.chat.completions.create(**kwargs)
        except Exception as e:  # network, rate limit, bad model id, auth
            return MoveResponse(ok=False, error=f"{type(e).__name__}: {e}")

        text = (resp.choices[0].message.content or "").strip().lower()
        move = _parse_move(text)
        if move is None:
            return MoveResponse(ok=False, error=f"unparseable reply: {text!r}")
        return MoveResponse(move=move, ok=True)

    return app
