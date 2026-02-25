"""OneStream IDE Agent — Orchestrator Service."""

import structlog
from fastapi import FastAPI
from contextlib import asynccontextmanager
from typing import AsyncGenerator

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("orchestrator.starting")
    yield
    logger.info("orchestrator.shutdown")


app = FastAPI(
    title="OneStream IDE Orchestrator",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": "orchestrator"}


@app.post("/api/chat")
async def chat(request: dict) -> dict:
    """Handle chat messages from the API gateway. Routes to LangGraph agents."""
    message = request.get("message", "")
    project_id = request.get("projectId")
    environment_id = request.get("environmentId")

    logger.info(
        "chat.received",
        message_length=len(message),
        project_id=project_id,
        environment_id=environment_id,
    )

    # TODO: Route to LangGraph orchestration graph
    return {
        "response": f"[Orchestrator placeholder] Received: {message}",
        "agent": "planning",
        "status": "not_implemented",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
