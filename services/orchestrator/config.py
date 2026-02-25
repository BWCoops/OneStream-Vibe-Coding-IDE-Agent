"""Configuration for the orchestrator service."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMConfig:
    provider: str  # "anthropic" or "vllm"
    model: str
    api_key: str
    vllm_endpoint: str
    generator_max_tokens: int = 8192
    reviewer_max_tokens: int = 16384  # 2x context for verification agent


@dataclass(frozen=True)
class ServiceConfig:
    host: str = "0.0.0.0"
    port: int = 8080
    database_url: str = ""
    redis_url: str = ""
    rabbitmq_url: str = ""
    langfuse_host: str = ""
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""


def load_llm_config() -> LLMConfig:
    return LLMConfig(
        provider=os.getenv("LLM_PROVIDER", "anthropic"),
        model=os.getenv("LLM_MODEL", "claude-sonnet-4-20250514"),
        api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        vllm_endpoint=os.getenv("VLLM_ENDPOINT", "http://localhost:8000"),
        generator_max_tokens=int(os.getenv("GENERATOR_MAX_TOKENS", "8192")),
        reviewer_max_tokens=int(os.getenv("REVIEWER_MAX_TOKENS", "16384")),
    )


def load_service_config() -> ServiceConfig:
    return ServiceConfig(
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8080")),
        database_url=os.getenv("DATABASE_URL", "postgresql://ide_agent:localdev@localhost:5432/onestream_ide"),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
        rabbitmq_url=os.getenv("RABBITMQ_URL", "amqp://ide_agent:localdev@localhost:5672"),
        langfuse_host=os.getenv("LANGFUSE_HOST", ""),
        langfuse_public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
        langfuse_secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
    )
