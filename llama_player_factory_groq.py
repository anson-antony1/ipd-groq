import os
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

class MoveRequest(BaseModel):
    opponent_id: str
    history: List[Dict]  # [{round, my_move, opponent_move}...]

class MoveResponse(BaseModel):
    move: str

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

def create_app(model_id: str) -> FastAPI:
    app = FastAPI(title=f"Llama Player via Groq: {model_id}")

    @app.post("/make_move", response_model=MoveResponse)
    async def make_move(request: MoveRequest):
        try:
            user_prompt = _history_to_prompt(request.history)
            resp = client.chat.completions.create(
                model=model_id,
                temperature=0.1,
                max_tokens=4,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            text = (resp.choices[0].message.content or "").strip().lower()
            if "cooperate" in text and "defect" not in text:
                return MoveResponse(move="cooperate")
            if "defect" in text:
                return MoveResponse(move="defect")
            return MoveResponse(move="defect")  # failsafe
        except Exception as e:
            print(f"[{model_id}] error: {e}")
            return MoveResponse(move="defect")
    return app
