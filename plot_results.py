import matplotlib.pyplot as plt

# Hardcoding results from your last run
rounds = list(range(1, 11))
scores_8b = [0,0,0,0,0,0,0,0,0,0]   # 8B never scored
scores_70b = [5,10,15,20,25,30,35,40,45,50]  # 70B defected every time

plt.plot(rounds, scores_8b, label="Llama 3.1 8B (Groq)", marker="o")
plt.plot(rounds, scores_70b, label="Llama 3.1 70B (Groq)", marker="s")

plt.xlabel("Round")
plt.ylabel("Score")
plt.title("IPD Tournament Results")
plt.legend()
plt.grid(True)
plt.savefig("results.png")
plt.show()
