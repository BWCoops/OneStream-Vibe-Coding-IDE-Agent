"""Base connector interface and mock implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
import structlog

logger = structlog.get_logger()


class BaseConnector(ABC):
    """Base class for all data pipeline connectors."""

    @abstractmethod
    async def execute(self, stage: dict, parameters: dict) -> dict:
        """Execute the connector operation for a pipeline stage."""
        ...

    @abstractmethod
    async def test_connection(self, config: dict) -> bool:
        """Test connectivity to the data source/target."""
        ...


class MockConnector(BaseConnector):
    """Mock connector for development/testing."""

    async def execute(self, stage: dict, parameters: dict) -> dict:
        logger.info("mock_connector.execute", stage_id=stage.get("id"))
        return {"rows_processed": 0, "status": "mock"}

    async def test_connection(self, config: dict) -> bool:
        return True
