"""Cross-encoder re-ranking for search result refinement."""

from __future__ import annotations

from dataclasses import dataclass

import structlog

logger = structlog.get_logger()


@dataclass
class RankedResult:
    content: str
    original_score: float
    rerank_score: float
    metadata: dict


class CrossEncoderReranker:
    """Re-ranks search results using a cross-encoder model.

    Cross-encoders process (query, document) pairs jointly, producing
    more accurate relevance scores than bi-encoder dot products alone.
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> None:
        self.model_name = model_name
        self._model = None

    def _load_model(self) -> None:
        """Lazy-load the cross-encoder model."""
        if self._model is not None:
            return
        try:
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(self.model_name)
            logger.info("reranker.model_loaded", model=self.model_name)
        except ImportError:
            logger.warning("reranker.model_unavailable", model=self.model_name)
            self._model = None

    async def rerank(
        self,
        query: str,
        results: list[dict],
        top_k: int = 10,
        content_key: str = "content",
    ) -> list[RankedResult]:
        """Re-rank search results using the cross-encoder.

        Args:
            query: The search query.
            results: List of search result dicts, each containing a content field.
            top_k: Number of top results to return.
            content_key: Key in result dict containing the text to score.

        Returns:
            Re-ranked results sorted by cross-encoder score.
        """
        if not results:
            return []

        self._load_model()

        if self._model is None:
            # Fallback: return results in original order with original scores
            logger.warning("reranker.fallback_to_original_order")
            return [
                RankedResult(
                    content=r.get(content_key, ""),
                    original_score=r.get("score", 0.0),
                    rerank_score=r.get("score", 0.0),
                    metadata={k: v for k, v in r.items() if k != content_key},
                )
                for r in results[:top_k]
            ]

        # Build (query, document) pairs for cross-encoder
        pairs = [(query, r.get(content_key, "")) for r in results]

        # Score all pairs
        scores = self._model.predict(pairs)

        # Combine with original results
        ranked = []
        for i, (result, score) in enumerate(zip(results, scores)):
            ranked.append(RankedResult(
                content=result.get(content_key, ""),
                original_score=result.get("score", 0.0),
                rerank_score=float(score),
                metadata={k: v for k, v in result.items() if k != content_key},
            ))

        # Sort by rerank score descending
        ranked.sort(key=lambda x: x.rerank_score, reverse=True)

        logger.info(
            "reranker.completed",
            input_count=len(results),
            output_count=min(top_k, len(ranked)),
        )

        return ranked[:top_k]
