# Iterated Prisoner's Dilemma Tournament — Meta Llama via Groq

This project runs an **Iterated Prisoner's Dilemma** tournament between two Meta Llama models served through the **Groq API**.  
It showcases how different AI models behave under repeated game-theory scenarios.

---

## 🧠 Models (Family Picked by Anson)
- **Llama 3.1 8B Instant** (Groq) — fast and cost-efficient
- **Llama 3.1 70B Versatile** (Groq) — larger, more powerful

---

## ⚙️ How to Run

1. **Clone the repo**
   ```bash
   git clone https://github.com/anson-antony1/ipd-groq.git
   cd ipd-groq
   
2.	**Set up environment**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
```
3. **Add your Groq API key**
  ```bash
Create a .env file in the project root:GROQ_API_KEY=grq_xxxxxxxxxxxxxxxxx
```
4.	Start model servers (Terminal A)
```bash
python groq_runner.py
```
5.	Run the tournament (Terminal B)
```bash
python tournament_engine.py
```

📊 Output
•	Console logs show round-by-round moves and final scores.
•	Results are saved in results.txt.
•	You can also generate a graph:python plot_results.py
