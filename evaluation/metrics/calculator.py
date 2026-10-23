import math
from collections.abc import Sequence


def calculate_percentiles(samples: Sequence[float]) -> dict[str, float | None]:
    """Calculates min, max, mean, p50, p95, and p99 for a sequence of numeric timings (in milliseconds)."""
    if not samples:
        return {
            "count": 0,
            "min": None,
            "max": None,
            "mean": None,
            "p50": None,
            "p95": None,
            "p99": None,
        }

    sorted_samples = sorted(samples)
    n = len(sorted_samples)

    def get_p(pct: float) -> float:
        if n == 1:
            return sorted_samples[0]
        k = (n - 1) * (pct / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_samples[int(k)]
        d0 = sorted_samples[int(f)] * (c - k)
        d1 = sorted_samples[int(c)] * (k - f)
        return round(d0 + d1, 3)

    return {
        "count": n,
        "min": round(sorted_samples[0], 3),
        "max": round(sorted_samples[-1], 3),
        "mean": round(sum(sorted_samples) / n, 3),
        "p50": get_p(50.0),
        "p95": get_p(95.0),
        "p99": get_p(99.0),
    }


def calculate_pass_rate(passed: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round((passed / total) * 100.0, 2)
