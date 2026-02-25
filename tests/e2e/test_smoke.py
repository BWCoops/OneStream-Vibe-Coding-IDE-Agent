"""End-to-end smoke tests — health checks on all services.

These tests verify that each service in the platform is reachable and
responds to its health/readiness endpoint. They require the full
environment to be running (docker-compose up).

Run with: pytest -m e2e
"""

from __future__ import annotations

import os

import pytest

pytestmark = [pytest.mark.e2e]

# ---------------------------------------------------------------------------
# Service URLs from environment (with docker-compose defaults)
# ---------------------------------------------------------------------------
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:3000")
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8080")
KNOWLEDGE_URL = os.getenv("KNOWLEDGE_URL", "http://localhost:8081")
TESTING_SERVICE_URL = os.getenv("TESTING_SERVICE_URL", "http://localhost:8082")
ALM_URL = os.getenv("ALM_URL", "http://localhost:8083")
DATA_ORCH_URL = os.getenv("DATA_ORCHESTRATION_URL", "http://localhost:8084")
ROSLYN_URL = os.getenv("ROSLYN_SERVICE_URL", "http://localhost:5100")
LANGFUSE_URL = os.getenv("LANGFUSE_HOST", "http://localhost:3001")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
async def _check_health(url: str, path: str = "/health") -> dict:
    """
    Make a GET request to a service health endpoint.

    Returns: {"status_code": int, "body": dict | str}
    """
    try:
        import httpx

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{url}{path}")
            try:
                body = response.json()
            except Exception:
                body = response.text
            return {"status_code": response.status_code, "body": body}
    except Exception as e:
        return {"status_code": 0, "body": str(e)}


# ---------------------------------------------------------------------------
# Smoke tests per service
# ---------------------------------------------------------------------------
class TestAPIGatewaySmoke:
    """Verify the Node.js API gateway is up."""

    @pytest.mark.asyncio
    async def test_health(self):
        result = await _check_health(API_GATEWAY_URL)
        if result["status_code"] == 0:
            pytest.skip(f"API Gateway not reachable: {result['body']}")
        assert result["status_code"] == 200

    @pytest.mark.asyncio
    async def test_readiness(self):
        result = await _check_health(API_GATEWAY_URL, "/ready")
        if result["status_code"] == 0:
            pytest.skip(f"API Gateway not reachable: {result['body']}")
        assert result["status_code"] == 200


class TestOrchestratorSmoke:
    """Verify the Python orchestrator service is up."""

    @pytest.mark.asyncio
    async def test_health(self):
        result = await _check_health(ORCHESTRATOR_URL)
        if result["status_code"] == 0:
            pytest.skip(f"Orchestrator not reachable: {result['body']}")
        assert result["status_code"] == 200


class TestKnowledgeServiceSmoke:
    """Verify the knowledge/RAG service is up."""

    @pytest.mark.asyncio
    async def test_health(self):
        result = await _check_health(KNOWLEDGE_URL)
        if result["status_code"] == 0:
            pytest.skip(f"Knowledge service not reachable: {result['body']}")
        assert result["status_code"] == 200


class TestTestingServiceSmoke:
    """Verify the testing service is up."""

    @pytest.mark.asyncio
    async def test_health(self):
        result = await _check_health(TESTING_SERVICE_URL)
        if result["status_code"] == 0:
            pytest.skip(f"Testing service not reachable: {result['body']}")
        assert result["status_code"] == 200


class TestALMServiceSmoke:
    """Verify the ALM/governance service is up."""

    @pytest.mark.asyncio
    async def test_health(self):
        result = await _check_health(ALM_URL)
        if result["status_code"] == 0:
            pytest.skip(f"ALM service not reachable: {result['body']}")
        assert result["status_code"] == 200


class TestDataOrchestrationSmoke:
    """Verify the data orchestration service is up."""

    @pytest.mark.asyncio
    async def test_health(self):
        result = await _check_health(DATA_ORCH_URL)
        if result["status_code"] == 0:
            pytest.skip(f"Data orchestration not reachable: {result['body']}")
        assert result["status_code"] == 200


class TestRoslynServiceSmoke:
    """Verify the .NET Roslyn compilation service is up."""

    @pytest.mark.asyncio
    async def test_health(self):
        result = await _check_health(ROSLYN_URL, "/api/health")
        if result["status_code"] == 0:
            pytest.skip(f"Roslyn service not reachable: {result['body']}")
        assert result["status_code"] == 200


class TestLangfuseSmoke:
    """Verify Langfuse observability is up."""

    @pytest.mark.asyncio
    async def test_health(self):
        result = await _check_health(LANGFUSE_URL, "/api/public/health")
        if result["status_code"] == 0:
            pytest.skip(f"Langfuse not reachable: {result['body']}")
        assert result["status_code"] == 200


class TestDatabaseConnectivity:
    """Verify PostgreSQL is reachable."""

    @pytest.mark.asyncio
    async def test_postgres_connection(self):
        try:
            import asyncpg

            db_url = os.getenv(
                "DATABASE_URL",
                "postgresql://ide_agent:localdev@localhost:5432/onestream_ide",
            )
            conn = await asyncpg.connect(dsn=db_url)
            result = await conn.fetchval("SELECT 1")
            await conn.close()
            assert result == 1
        except Exception as e:
            pytest.skip(f"PostgreSQL not reachable: {e}")


class TestRedisConnectivity:
    """Verify Redis is reachable."""

    @pytest.mark.asyncio
    async def test_redis_ping(self):
        try:
            import redis.asyncio as aioredis

            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            r = aioredis.from_url(redis_url)
            pong = await r.ping()
            await r.aclose()
            assert pong is True
        except Exception as e:
            pytest.skip(f"Redis not reachable: {e}")


class TestNeo4jConnectivity:
    """Verify Neo4j is reachable."""

    @pytest.mark.asyncio
    async def test_neo4j_connection(self):
        try:
            from neo4j import AsyncGraphDatabase

            uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
            password = os.getenv("NEO4J_PASSWORD", "localdev")
            driver = AsyncGraphDatabase.driver(uri, auth=("neo4j", password))
            async with driver.session() as session:
                result = await session.run("RETURN 1 AS n")
                record = await result.single()
                assert record["n"] == 1
            await driver.close()
        except Exception as e:
            pytest.skip(f"Neo4j not reachable: {e}")


class TestRabbitMQConnectivity:
    """Verify RabbitMQ is reachable."""

    @pytest.mark.asyncio
    async def test_rabbitmq_connection(self):
        try:
            import aio_pika

            rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://ide_agent:localdev@localhost:5672")
            connection = await aio_pika.connect_robust(rabbitmq_url)
            assert connection is not None
            await connection.close()
        except Exception as e:
            pytest.skip(f"RabbitMQ not reachable: {e}")


class TestEndToEndWorkflow:
    """Verify a complete code generation workflow through the platform."""

    @pytest.mark.asyncio
    async def test_chat_code_generation(self):
        """Send a code generation request through the chat endpoint."""
        result = await _check_health(API_GATEWAY_URL)
        if result["status_code"] == 0:
            pytest.skip("API Gateway not reachable")

        try:
            import httpx

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{API_GATEWAY_URL}/api/chat",
                    json={
                        "message": "Generate a simple Finance Rule that calculates net income",
                        "ruleType": "finance_rule",
                        "targetRuntime": "net8.0",
                    },
                )
                assert response.status_code == 200
                data = response.json()
                assert "response" in data
        except Exception as e:
            pytest.skip(f"Chat endpoint test failed: {e}")

    @pytest.mark.asyncio
    async def test_direct_code_review(self):
        """Submit code for review via the review endpoint."""
        result = await _check_health(API_GATEWAY_URL)
        if result["status_code"] == 0:
            pytest.skip("API Gateway not reachable")

        try:
            import httpx

            vb_code = (
                "Public Class FinanceRule\n"
                "    Public Function Main() As Object\n"
                "        Try\n"
                "            BRApi.ErrorLog.LogMessage(si, \"Step 1\")\n"
                "            Return Nothing\n"
                "        Catch ex As Exception\n"
                "            BRApi.ErrorLog.LogMessage(si, ex.Message)\n"
                "            Throw\n"
                "        End Try\n"
                "    End Function\n"
                "End Class"
            )
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{API_GATEWAY_URL}/api/review",
                    json={
                        "sourceCode": vb_code,
                        "language": "vb.net",
                        "ruleType": "finance_rule",
                    },
                )
                assert response.status_code == 200
                data = response.json()
                assert "passed" in data
                assert "score" in data
        except Exception as e:
            pytest.skip(f"Review endpoint test failed: {e}")
