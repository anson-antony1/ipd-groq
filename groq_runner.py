"""Serve each Llama model as its own FastAPI player on its own port.

Model ids are read from the environment so a retired model can be swapped
without editing code:

    IPD_MODEL_A=llama-3.1-8b-instant   IPD_PORT_A=8041
    IPD_MODEL_B=llama-3.3-70b-versatile IPD_PORT_B=8042
"""

import multiprocessing
import os

import uvicorn

from llama_player_factory_groq import create_app

# llama-3.1-70b-versatile was retired from Groq's lineup; 3.3 70B is the
# successor. Check https://console.groq.com/docs/models before a run.
DEFAULT_MODEL_A = "llama-3.1-8b-instant"
DEFAULT_MODEL_B = "llama-3.3-70b-versatile"


def run_server(model_id: str, port: int) -> None:
    app = create_app(model_id)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    configs = [
        (os.getenv("IPD_MODEL_A", DEFAULT_MODEL_A), int(os.getenv("IPD_PORT_A", "8041"))),
        (os.getenv("IPD_MODEL_B", DEFAULT_MODEL_B), int(os.getenv("IPD_PORT_B", "8042"))),
    ]
    for model_id, port in configs:
        print(f"serving {model_id} on http://127.0.0.1:{port}")

    procs = []
    for model_id, port in configs:
        p = multiprocessing.Process(target=run_server, args=(model_id, port))
        p.start()
        procs.append(p)
    try:
        for p in procs:
            p.join()
    except KeyboardInterrupt:
        for p in procs:
            p.terminate()
