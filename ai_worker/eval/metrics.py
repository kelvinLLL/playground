from typing import List, Set, Dict, Any
import math
import statistics


def precision_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """
    Calculate Precision@K.
    P@K = (# of relevant items in top K) / K
    """
    if k <= 0:
        return 0.0

    retrieved_k = retrieved[:k]
    if not retrieved_k:
        return 0.0

    hits = sum(1 for r in retrieved_k if r in relevant)
    return hits / k


def recall_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """
    Calculate Recall@K.
    R@K = (# of relevant items in top K) / (Total relevant items)
    """
    if not relevant:
        return 0.0

    retrieved_k = retrieved[:k]
    hits = sum(1 for r in retrieved_k if r in relevant)
    return hits / len(relevant)


def mrr(retrieved: List[str], relevant: Set[str]) -> float:
    """
    Calculate Mean Reciprocal Rank (MRR).
    MRR = 1 / (rank of first relevant item)
    """
    for i, r in enumerate(retrieved, 1):
        if r in relevant:
            return 1.0 / i
    return 0.0


def latency_stats(times_ms: List[float]) -> Dict[str, float]:
    """
    Calculate latency statistics.
    """
    if not times_ms:
        return {"mean": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0}

    sorted_times = sorted(times_ms)
    n = len(sorted_times)

    return {
        "mean": statistics.mean(sorted_times),
        "p50": statistics.median(sorted_times),
        "p95": sorted_times[int(n * 0.95)],
        "p99": sorted_times[int(n * 0.99)],
    }


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Estimate token count.
    Uses tiktoken if available, otherwise simple approximation.
    """
    try:
        import tiktoken

        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except ImportError:
        # Fallback: ~4 chars per token for English
        return len(text) // 4
