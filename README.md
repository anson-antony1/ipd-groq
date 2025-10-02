# IPD Tournament — Meta Llama via Groq

This repo runs an Iterated Prisoner's Dilemma tournament between two Meta Llama models served through the Groq API.

## Models (family picked by Anson)
- Llama 3.1 8B Instant (Groq)
- Llama 3.1 70B Versatile (Groq)

## How to run
1. Put your Groq key in .env:GROQ_API_KEY=grq_xxxxxxxxx
2. Install deps:pip install -r requirements.txt
3. Start players (Terminal A):python groq_runner.py
4. Run tournament (Terminal B):python tournament_engine.py
## Output
- Console logs show round-by-round moves and final scores.
