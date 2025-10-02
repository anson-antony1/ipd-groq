import multiprocessing
import uvicorn
from llama_player_factory_groq import create_app

def run_server(model_id, port):
    app = create_app(model_id)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

if __name__ == "__main__":
    # Two Llama models (popular + cheap) via Groq API
    configs = [
        ("llama-3.1-8b-instant", 8041),     # fast/cheap
        ("llama-3.1-70b-versatile", 8042),  # stronger
    ]
    procs = []
    for model_id, port in configs:
        p = multiprocessing.Process(target=run_server, args=(model_id, port))
        p.start()
        procs.append(p)
    for p in procs:
        p.join()
