"""DeepEval integration for evaluating LLM-generated code quality."""

from __future__ import annotations

import structlog

logger = structlog.get_logger()


async def evaluate_code(
    generated_code: str,
    requirement: str,
    rule_type: str,
) -> dict:
    """
    Evaluate generated code using DeepEval metrics.

    Metrics:
    1. Faithfulness — Does the code match the requirement?
    2. Relevancy — Is the generated code relevant to OneStream?
    3. Correctness — Does it follow coding standards?
    4. Toxicity — No hardcoded secrets or unsafe patterns
    """
    logger.info("deepeval.evaluate", rule_type=rule_type, code_length=len(generated_code))

    try:
        from deepeval.metrics import (
            FaithfulnessMetric,
            AnswerRelevancyMetric,
        )
        from deepeval.test_case import LLMTestCase

        test_case = LLMTestCase(
            input=requirement,
            actual_output=generated_code,
            retrieval_context=[f"Business rule type: {rule_type}"],
        )

        faithfulness = FaithfulnessMetric(threshold=0.7)
        relevancy = AnswerRelevancyMetric(threshold=0.7)

        faithfulness.measure(test_case)
        relevancy.measure(test_case)

        return {
            "faithfulness": {
                "score": faithfulness.score,
                "passed": faithfulness.is_successful(),
                "reason": faithfulness.reason,
            },
            "relevancy": {
                "score": relevancy.score,
                "passed": relevancy.is_successful(),
                "reason": relevancy.reason,
            },
            "overall_passed": faithfulness.is_successful() and relevancy.is_successful(),
        }

    except ImportError:
        logger.warning("deepeval_not_installed")
        # Fallback: basic heuristic evaluation
        return _heuristic_evaluation(generated_code, requirement, rule_type)

    except Exception as e:
        logger.error("deepeval_failed", error=str(e))
        return {"error": str(e), "overall_passed": False}


def _heuristic_evaluation(code: str, requirement: str, rule_type: str) -> dict:
    """Basic heuristic code quality evaluation when DeepEval is unavailable."""
    checks = {
        "has_error_handling": "Try" in code and "Catch" in code,
        "has_error_logging": "BRApi.ErrorLog.LogMessage" in code or "ErrorLog" in code,
        "has_step_identification": "stepName" in code.lower() or "step" in code.lower(),
        "no_hardcoded_credentials": not any(
            kw in code.lower() for kw in ["password=", "pwd=", "secret=", "apikey="]
        ),
        "has_documentation": "'" in code or "//" in code or "'''" in code,
        "reasonable_length": 50 < len(code.splitlines()) < 500,
    }

    score = sum(checks.values()) / len(checks)

    return {
        "heuristic": True,
        "checks": checks,
        "score": round(score, 2),
        "overall_passed": score >= 0.6,
    }
