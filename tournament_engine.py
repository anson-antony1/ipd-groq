import requests
from itertools import combinations
import logging
import time

PAYOFF_MATRIX = {
    ("cooperate", "cooperate"): (3, 3),   # R
    ("cooperate", "defect"): (0, 5),     # S, T
    ("defect", "cooperate"): (5, 0),     # T, S
    ("defect", "defect"): (1, 1),        # P
}

class TournamentEngine:
    def __init__(self, players, rounds_per_match=10):
        self.players = players
        self.rounds_per_match = rounds_per_match
        self.scores = {player['name']: 0 for player in players}

    def play_match(self, player_a, player_b):
        history_a = []
        history_b = []
        score_a, score_b = 0, 0
        
        print(f"\n{'='*60}")
        print(f"🏁  Starting Match: {player_a['name']}  vs  {player_b['name']}")
        print(f"{'='*60}")

        for round_num in range(1, self.rounds_per_match + 1):
            payload_a = {"opponent_id": player_b['name'], "history": history_a}
            payload_b = {"opponent_id": player_a['name'], "history": history_b}

            move_a = self.get_move(player_a['url'], payload_a)
            move_b = self.get_move(player_b['url'], payload_b)

            payoff_a, payoff_b = PAYOFF_MATRIX.get((move_a, move_b), (1, 1))
            prev_score_a, prev_score_b = score_a, score_b
            score_a += payoff_a
            score_b += payoff_b

            print(f"\nRound {round_num:>2}: ")
            print(f"  {player_a['name']:<28} chose '{move_a.upper()}'   (+{payoff_a})   |   {player_b['name']} chose '{move_b.upper()}'  (+{payoff_b})")
            print(f"  {player_a['name']:<28} Score: {prev_score_a}  →  {score_a}")
            print(f"  {player_b['name']:<28} Score: {prev_score_b}  →  {score_b}")

            history_a.append({"round": round_num, "my_move": move_a, "opponent_move": move_b})
            history_b.append({"round": round_num, "my_move": move_b, "opponent_move": move_a})

            time.sleep(0.5)
            
        self.scores[player_a['name']] += score_a
        self.scores[player_b['name']] += score_b
        
        print(f"{'-'*60}")
        print(f"🏆  Match Over: {player_a['name']} vs {player_b['name']} | Final Score: {score_a} - {score_b}")
        print(f"{'='*60}\n")

    def get_move(self, url, payload):
        try:
            resp = requests.post(f"{url}/make_move", json=payload, timeout=10)
            response_json = resp.json()
            move = response_json.get("move", "defect").lower()
            if move not in ("cooperate", "defect"):
                return "defect"
            return move
        except requests.exceptions.Timeout:
            print(f"  ❌ Request to {url} timed out.")
            return "defect"
        except Exception as e:
            print(f"  ❌ Error getting move from {url}: {e}")
            return "defect"

    def run_tournament(self):
        for player_a, player_b in combinations(self.players, 2):
            self.play_match(player_a, player_b)
        
        print(f"\n{'#'*60}")
        print("🏁  TOURNAMENT FINAL SCORES:")
        print(f"{'#'*60}")
        for name, score in sorted(self.scores.items(), key=lambda item: item[1], reverse=True):
            print(f"  {name:<35} : {score}")
        print(f"{'#'*60}\n")

if __name__ == "__main__":
    players = [
        {"name": "Llama 3.1 8B (Groq)", "url": "http://localhost:8041"},
        {"name": "Llama 3.1 70B (Groq)", "url": "http://localhost:8042"}
    ]
    
    engine = TournamentEngine(players)
    engine.run_tournament()
