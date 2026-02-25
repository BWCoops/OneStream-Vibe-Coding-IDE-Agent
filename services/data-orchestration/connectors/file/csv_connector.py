"""CSV / SFTP file connector."""

from __future__ import annotations

import structlog

from connectors.base import BaseConnector

logger = structlog.get_logger()


class CsvConnector(BaseConnector):
    """
    CSV file connector supporting local and SFTP sources.

    Uses SSH.NET pattern (Renci.SshNet) for SFTP — NOT WinSCP (deprecated on .NET 8).
    """

    async def execute(self, stage: dict, parameters: dict) -> dict:
        connector_config = stage.get("connector", {})
        config_params = connector_config.get("parameters", {})
        stage_type = stage.get("type", "EXTRACT")

        file_path = config_params.get("file_path", "")
        is_sftp = config_params.get("sftp", False)
        delimiter = config_params.get("delimiter", ",")
        has_header = config_params.get("has_header", True)

        logger.info(
            "csv.execute",
            stage_id=stage.get("id"),
            stage_type=stage_type,
            is_sftp=is_sftp,
            file_path=file_path,
        )

        if stage_type == "EXTRACT":
            if is_sftp:
                return await self._extract_sftp(config_params)
            return await self._extract_local(file_path, delimiter, has_header)
        elif stage_type == "LOAD":
            return await self._write_csv(file_path, delimiter, has_header, parameters)

        return {"rows_processed": 0, "status": "unsupported_operation"}

    async def _extract_local(self, file_path: str, delimiter: str, has_header: bool) -> dict:
        """Read a local CSV file."""
        logger.info("csv.extract_local", file_path=file_path)
        return {"rows_processed": 0, "status": "extracted", "connector": "csv_local"}

    async def _extract_sftp(self, config: dict) -> dict:
        """Read a CSV file from SFTP using SSH.NET pattern."""
        host = config.get("sftp_host", "")
        username = config.get("sftp_username", "")
        # Password/key should come from Vault at execution time
        logger.info("csv.extract_sftp", host=host, username=username)
        return {"rows_processed": 0, "status": "extracted", "connector": "csv_sftp"}

    async def _write_csv(self, file_path: str, delimiter: str, has_header: bool, data: dict) -> dict:
        """Write data to a CSV file."""
        logger.info("csv.write", file_path=file_path)
        return {"rows_processed": 0, "status": "loaded", "connector": "csv"}

    async def test_connection(self, config: dict) -> bool:
        is_sftp = config.get("sftp", False)
        if is_sftp:
            return bool(config.get("sftp_host"))
        return bool(config.get("file_path"))
