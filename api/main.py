from fastapi import FastAPI

app = FastAPI(title="Autonomous Agentic OS")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
