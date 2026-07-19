from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from dataclasses import dataclass, field
from typing import Callable

logger = logging.getLogger(__name__)

TASK_TYPE_WEIGHTS: dict[str, dict[str, float]] = {
    "reason": {"confidence": 0.6, "latency": 0.1, "agreement": 0.3},
    "classify": {"confidence": 0.5, "latency": 0.05, "agreement": 0.45},
    "extract": {"confidence": 0.7, "latency": 0.1, "agreement": 0.2},
    "generate": {"confidence": 0.4, "latency": 0.2, "agreement": 0.4},
    "decide": {"confidence": 0.8, "latency": 0.05, "agreement": 0.15},
    "default": {"confidence": 0.5, "latency": 0.1, "agreement": 0.4},
}


@dataclass(frozen=True, slots=True)
class CouncilVote:
    model_id: str
    answer: str
    confidence: float
    reasoning: str
    latency_ms: int


@dataclass(frozen=True, slots=True)
class CouncilVerdict:
    answer: str
    confidence: float
    agreement_ratio: float
    votes: list[CouncilVote] = field(repr=False)
    method: str


class ModelCouncil:
    def __init__(
        self,
        models: list[str] | None = None,
        min_votes: int = 2,
        timeout_per_model_ms: int = 30000,
    ) -> None:
        self._models: list[str] = list(models) if models else []
        self._min_votes = min_votes
        self._timeout_ms = timeout_per_model_ms
        self._model_executor: Callable[[str, str], str] | None = None

    def set_executor(self, executor: Callable[[str, str], str]) -> None:
        self._model_executor = executor

    def add_model(self, model_id: str) -> None:
        if model_id not in self._models:
            self._models.append(model_id)
            logger.info("Council: added model %s", model_id)

    def remove_model(self, model_id: str) -> None:
        if model_id in self._models:
            self._models.remove(model_id)
            logger.info("Council: removed model %s", model_id)

    def get_models(self) -> list[str]:
        return list(self._models)

    def deliberate(
        self,
        prompt: str,
        task_type: str = "reason",
        method: str = "weighted",
    ) -> CouncilVerdict:
        if not self._models:
            logger.warning("Council: no models registered, returning empty verdict")
            return CouncilVerdict(
                answer="",
                confidence=0.0,
                agreement_ratio=0.0,
                votes=[],
                method=method,
            )

        votes = self._gather_votes(prompt)
        if not votes:
            logger.warning("Council: no votes collected, returning empty verdict")
            return CouncilVerdict(
                answer="",
                confidence=0.0,
                agreement_ratio=0.0,
                votes=[],
                method=method,
            )

        if method == "majority":
            verdict = self._majority_vote(votes, method)
        elif method == "best_confidence":
            verdict = self._best_confidence(votes, method)
        else:
            verdict = self._weighted_vote(votes, task_type, method)
        logger.info(
            "Council verdict via %s: %s (conf=%.2f, agree=%.2f, votes=%d)",
            method,
            verdict.answer[:80],
            verdict.confidence,
            verdict.agreement_ratio,
            len(votes),
        )
        return verdict

    def _gather_votes(self, prompt: str) -> list[CouncilVote]:
        votes: list[CouncilVote] = []
        max_workers = min(len(self._models), 8)

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(self._call_model, model_id, prompt, self._timeout_ms): model_id
                for model_id in self._models
            }

            for future in futures:
                model_id = futures[future]
                try:
                    vote = future.result(timeout=self._timeout_ms / 1000)
                    if vote is not None:
                        votes.append(vote)
                except FuturesTimeout:
                    logger.warning(
                        "Council: model %s timed out after %dms", model_id, self._timeout_ms
                    )
                except Exception:
                    logger.exception("Council: model %s raised an exception", model_id)

        if len(votes) < self._min_votes:
            logger.warning(
                "Council: only %d votes (min=%d), verdict may be unreliable",
                len(votes),
                self._min_votes,
            )

        return votes

    def _call_model(self, model_id: str, prompt: str, timeout_ms: int) -> CouncilVote:
        start = time.monotonic()

        if self._model_executor is not None:
            try:
                raw = self._model_executor(model_id, prompt)
                elapsed = int((time.monotonic() - start) * 1000)
                return CouncilVote(
                    model_id=model_id,
                    answer=str(raw.get("answer", "")) if isinstance(raw, dict) else str(raw),
                    confidence=float(raw.get("confidence", 0.5)) if isinstance(raw, dict) else 0.5,
                    reasoning=str(raw.get("reasoning", "")) if isinstance(raw, dict) else "",
                    latency_ms=elapsed,
                )
            except Exception:
                logger.exception("Council: executor failed for model %s", model_id)
                elapsed = int((time.monotonic() - start) * 1000)
                return CouncilVote(
                    model_id=model_id,
                    answer="",
                    confidence=0.0,
                    reasoning=f"executor error for {model_id}",
                    latency_ms=elapsed,
                )

        logger.warning("Council: no executor set, returning dummy vote for %s", model_id)
        elapsed = int((time.monotonic() - start) * 1000)
        return CouncilVote(
            model_id=model_id,
            answer="[stub] no executor configured",
            confidence=0.0,
            reasoning="model executor not wired",
            latency_ms=elapsed,
        )

    def _majority_vote(self, votes: list[CouncilVote], method: str = "majority") -> CouncilVerdict:
        tally: dict[str, list[CouncilVote]] = {}
        for v in votes:
            normalized = v.answer.strip().lower()
            tally.setdefault(normalized, []).append(v)

        best_key = max(tally, key=lambda k: len(tally[k]))
        winner_votes = tally[best_key]
        agreement_ratio = len(winner_votes) / len(votes) if votes else 0.0
        avg_confidence = sum(v.confidence for v in winner_votes) / len(winner_votes) if winner_votes else 0.0

        return CouncilVerdict(
            answer=winner_votes[0].answer,
            confidence=avg_confidence,
            agreement_ratio=agreement_ratio,
            votes=votes,
            method=method,
        )

    def _weighted_vote(self, votes: list[CouncilVote], task_type: str = "reason", method: str = "weighted") -> CouncilVerdict:
        weights = TASK_TYPE_WEIGHTS.get(task_type, TASK_TYPE_WEIGHTS["default"])

        scored: list[tuple[CouncilVote, float]] = []
        max_latency = max((v.latency_ms for v in votes), default=1) or 1

        for v in votes:
            score = 0.0
            score += v.confidence * weights["confidence"]
            speed_factor = 1.0 - (v.latency_ms / max_latency) if max_latency > 0 else 1.0
            score += speed_factor * weights["latency"]
            score += weights["agreement"]
            scored.append((v, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        best_vote, best_score = scored[0]

        tally: dict[str, int] = {}
        for v in votes:
            key = v.answer.strip().lower()
            tally[key] = tally.get(key, 0) + 1
        agreement_count = tally.get(best_vote.answer.strip().lower(), 0)
        agreement_ratio = agreement_count / len(votes) if votes else 0.0

        return CouncilVerdict(
            answer=best_vote.answer,
            confidence=best_vote.confidence,
            agreement_ratio=agreement_ratio,
            votes=votes,
            method=method,
        )

    def _best_confidence(self, votes: list[CouncilVote], method: str = "best_confidence") -> CouncilVerdict:
        if not votes:
            return CouncilVerdict(
                answer="",
                confidence=0.0,
                agreement_ratio=0.0,
                votes=[],
                method=method,
            )

        best = max(votes, key=lambda v: v.confidence)
        agreement_ratio = sum(1 for v in votes if v.answer.strip().lower() == best.answer.strip().lower()) / len(votes)

        return CouncilVerdict(
            answer=best.answer,
            confidence=best.confidence,
            agreement_ratio=agreement_ratio,
            votes=votes,
            method=method,
        )


ARES_COUNCIL = ModelCouncil()


def deliberate(
    prompt: str,
    task_type: str = "reason",
    method: str = "weighted",
) -> CouncilVerdict:
    return ARES_COUNCIL.deliberate(prompt, task_type=task_type, method=method)
