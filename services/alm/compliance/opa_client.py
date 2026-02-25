"""OPA (Open Policy Agent) client for policy-as-code compliance enforcement."""

from __future__ import annotations

import os

import httpx
import structlog

logger = structlog.get_logger()

OPA_ENDPOINT = os.getenv("OPA_ENDPOINT", "http://localhost:8181")


async def check_policy(policy_path: str, input_data: dict) -> dict:
    """
    Query OPA for a policy decision.

    Args:
        policy_path: OPA policy path (e.g., "sox/itgc", "deployment/gates", "dora/resilience")
        input_data: Input data for the policy evaluation

    Returns:
        Policy decision including allow/deny and violation messages
    """
    url = f"{OPA_ENDPOINT}/v1/data/{policy_path.replace('/', '.')}"

    logger.info("opa.check_policy", policy=policy_path)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                json={"input": input_data},
            )
            response.raise_for_status()
            result = response.json().get("result", {})

            logger.info(
                "opa.policy_result",
                policy=policy_path,
                allowed=result.get("allow", False),
                violations=len(result.get("deny", [])),
            )

            return result

    except httpx.ConnectError:
        logger.warning("opa.unavailable", endpoint=OPA_ENDPOINT)
        # Fail-open in development, fail-closed in production
        if os.getenv("ENV", "development") == "production":
            return {"allow": False, "deny": ["OPA service unavailable — fail-closed in production"]}
        return {"allow": True, "deny": [], "warning": "OPA unavailable — fail-open in development"}

    except Exception as e:
        logger.error("opa.check_failed", error=str(e))
        return {"allow": False, "deny": [f"Policy check failed: {e}"]}
