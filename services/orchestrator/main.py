"""OneStream IDE Agent — Orchestrator Service."""

from __future__ import annotations

import structlog
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import load_llm_config, load_service_config
from llm_client import LLMClient
from graphs.code_gen_flow import code_gen_graph

logger = structlog.get_logger()

# Global LLM client instance
llm_client: LLMClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global llm_client
    llm_config = load_llm_config()
    llm_client = LLMClient(llm_config)
    logger.info("orchestrator.starting", llm_provider=llm_config.provider, model=llm_config.model)
    yield
    if llm_client:
        await llm_client.close()
    logger.info("orchestrator.shutdown")


app = FastAPI(
    title="OneStream IDE Orchestrator",
    version="0.1.0",
    lifespan=lifespan,
)


# ── Request/Response Models ──


class ChatRequest(BaseModel):
    message: str
    projectId: str | None = None
    environmentId: str | None = None
    ruleType: str = "finance_rule"
    targetRuntime: str = "net8.0"


class CodeGenRequest(BaseModel):
    requirement: str
    ruleType: str = "finance_rule"
    targetRuntime: str = "net8.0"
    projectContext: dict = {}


class ReviewRequest(BaseModel):
    sourceCode: str
    language: str = "vb.net"
    ruleType: str = "finance_rule"
    targetRuntime: str = "net8.0"
    originalRequirement: str = ""


# ── Routes ──


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": "orchestrator"}


@app.post("/api/chat")
async def chat(request: ChatRequest) -> dict:
    """Handle chat messages — routes to the appropriate agent graph."""
    if not llm_client:
        raise HTTPException(status_code=503, detail="LLM client not initialized")

    logger.info(
        "chat.received",
        message_length=len(request.message),
        project_id=request.projectId,
    )

    # Determine intent: code generation, review, migration, etc.
    message_lower = request.message.lower()

    if any(kw in message_lower for kw in ["generate", "create", "write", "build"]):
        return await _run_code_gen(request)
    elif any(kw in message_lower for kw in ["review", "check", "validate"]):
        return {
            "response": "To review code, use the /api/review endpoint with your source code.",
            "agent": "routing",
            "status": "redirect",
        }
    else:
        # General conversation — use planning agent for clarification
        response = await llm_client.generate(
            system_prompt=(
                "You are an AI assistant for the OneStream XF platform. "
                "Help users with business rule development, data orchestration, "
                "and platform questions. Be concise and technical."
            ),
            user_message=request.message,
            max_tokens=2048,
        )
        return {
            "response": response,
            "agent": "assistant",
            "status": "complete",
        }


async def _run_code_gen(request: ChatRequest) -> dict:
    """Execute the code generation graph."""
    compiled = code_gen_graph.compile()

    initial_state = {
        "requirement": request.message,
        "rule_type": request.ruleType,
        "target_runtime": request.targetRuntime,
        "project_context": {},
        "retry_count": 0,
        "test_cases": [],
        "_llm": llm_client,
    }

    result = await compiled.ainvoke(initial_state)

    return {
        "response": result.get("final_code", ""),
        "agent": "code_generator",
        "status": result.get("final_status", "unknown"),
        "review_score": result.get("review_score", 0.0),
        "review_findings": result.get("review_findings", []),
        "test_cases": result.get("test_cases", []),
    }


@app.post("/api/generate")
async def generate_code(request: CodeGenRequest) -> dict:
    """Direct code generation endpoint."""
    if not llm_client:
        raise HTTPException(status_code=503, detail="LLM client not initialized")

    compiled = code_gen_graph.compile()

    initial_state = {
        "requirement": request.requirement,
        "rule_type": request.ruleType,
        "target_runtime": request.targetRuntime,
        "project_context": request.projectContext,
        "retry_count": 0,
        "test_cases": [],
        "_llm": llm_client,
    }

    result = await compiled.ainvoke(initial_state)

    return {
        "code": result.get("final_code", ""),
        "status": result.get("final_status", "unknown"),
        "review_score": result.get("review_score", 0.0),
        "review_findings": result.get("review_findings", []),
        "test_cases": result.get("test_cases", []),
        "retry_count": result.get("retry_count", 0),
    }


@app.post("/api/review")
async def review_code(request: ReviewRequest) -> dict:
    """Direct code review endpoint."""
    if not llm_client:
        raise HTTPException(status_code=503, detail="LLM client not initialized")

    from agents.code_reviewer import ReviewRequest as CRRequest, review_code as do_review

    cr_request = CRRequest(
        source_code=request.sourceCode,
        language=request.language,
        target_runtime=request.targetRuntime,
        rule_type=request.ruleType,
        original_requirement=request.originalRequirement,
    )

    result = await do_review(llm_client, cr_request)

    return {
        "passed": result.passed,
        "score": result.score,
        "summary": result.summary,
        "findings": [
            {
                "category": f.category.value,
                "severity": f.severity.value,
                "message": f.message,
                "line": f.line,
                "suggestion": f.suggestion,
            }
            for f in result.findings
        ],
    }


if __name__ == "__main__":
    import uvicorn

    service_config = load_service_config()
    uvicorn.run(app, host=service_config.host, port=service_config.port)
