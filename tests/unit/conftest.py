"""Shared fixtures for unit tests — mock LLM client, mock DB, common helpers."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path manipulation so imports match how the services import each other.
# In production these would be resolved via PYTHONPATH or package installs.
# ---------------------------------------------------------------------------
_SERVICES_DIR = Path(__file__).resolve().parent.parent.parent / "services"

# Orchestrator service needs its own root on sys.path so that
# ``from llm_client import LLMClient`` and ``from config import LLMConfig``
# resolve correctly.
_ORCHESTRATOR_DIR = _SERVICES_DIR / "orchestrator"
if str(_ORCHESTRATOR_DIR) not in sys.path:
    sys.path.insert(0, str(_ORCHESTRATOR_DIR))

# Data-orchestration service
_DATA_ORCH_DIR = _SERVICES_DIR / "data-orchestration"
if str(_DATA_ORCH_DIR) not in sys.path:
    sys.path.insert(0, str(_DATA_ORCH_DIR))

# ALM service
_ALM_DIR = _SERVICES_DIR / "alm"
if str(_ALM_DIR) not in sys.path:
    sys.path.insert(0, str(_ALM_DIR))

# Testing service
_TESTING_DIR = _SERVICES_DIR / "testing"
if str(_TESTING_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTING_DIR))

# Knowledge service
_KNOWLEDGE_DIR = _SERVICES_DIR / "knowledge"
if str(_KNOWLEDGE_DIR) not in sys.path:
    sys.path.insert(0, str(_KNOWLEDGE_DIR))


# ---------------------------------------------------------------------------
# LLM Configuration fixture
# ---------------------------------------------------------------------------
@pytest.fixture
def llm_config():
    """Return a minimal LLMConfig for testing."""
    from config import LLMConfig

    return LLMConfig(
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        api_key="test-api-key-not-real",
        vllm_endpoint="http://localhost:8000",
        generator_max_tokens=8192,
        reviewer_max_tokens=16384,
    )


@pytest.fixture
def vllm_config():
    """Return an LLMConfig configured for vLLM."""
    from config import LLMConfig

    return LLMConfig(
        provider="vllm",
        model="qwen2.5-coder-7b",
        api_key="",
        vllm_endpoint="http://localhost:8000",
        generator_max_tokens=4096,
        reviewer_max_tokens=8192,
    )


# ---------------------------------------------------------------------------
# Mock LLM Client
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_llm_client(llm_config):
    """
    Return an LLMClient whose ``generate`` method is an AsyncMock.

    The caller can configure the return value per-test:
        mock_llm_client.generate.return_value = "Public Sub Main()..."
    """
    from llm_client import LLMClient

    client = LLMClient(llm_config)
    client.generate = AsyncMock(return_value="' default mock response")
    client._http = MagicMock()  # prevent real HTTP calls
    return client


# ---------------------------------------------------------------------------
# Mock Database connection
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_db_conn():
    """
    Return a mock asyncpg connection with common query helpers.

    Usage:
        mock_db_conn.fetchrow.return_value = {"id": 1, "status": "pending"}
    """
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetch = AsyncMock(return_value=[])
    conn.execute = AsyncMock()
    conn.close = AsyncMock()
    return conn


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_vbnet_code() -> str:
    """Return a sample VB.NET business rule for testing."""
    return """\
Public Sub Main()
    Try
        Dim api As New OneStream.BRApi
        Dim entityName As String = api.Pov.Entity.Name

        If entityName = "US_East" Then
            api.Data.SetDataCell(1000.0)
        End If

    Catch ex As Exception
        BRApi.ErrorLog.LogMessage(ex.Message)
    Finally
        ' cleanup
    End Try
End Sub
"""


@pytest.fixture
def sample_csharp_code() -> str:
    """Return a sample C# business rule for testing."""
    return """\
public void Main()
{
    try
    {
        var api = new OneStream.BRApi();
        var entityName = api.Pov.Entity.Name;

        if (entityName == "US_East")
        {
            api.Data.SetDataCell(1000.0);
        }
    }
    catch (Exception ex)
    {
        BRApi.ErrorLog.LogMessage(ex.Message);
    }
}
"""


@pytest.fixture
def simple_pipeline_definition() -> dict:
    """Return a valid three-stage pipeline definition."""
    return {
        "id": "pipeline-001",
        "name": "Test Pipeline",
        "stages": [
            {
                "id": "extract_1",
                "type": "EXTRACT",
                "dependencies": [],
                "connector": {"type": "csv"},
            },
            {
                "id": "transform_1",
                "type": "TRANSFORM",
                "dependencies": ["extract_1"],
                "connector": {"type": "sql"},
            },
            {
                "id": "load_1",
                "type": "LOAD",
                "dependencies": ["transform_1"],
                "connector": {"type": "onestream"},
            },
        ],
    }
