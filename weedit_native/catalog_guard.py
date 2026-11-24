"""Catalog usage guard shared by resolver implementations."""
from __future__ import annotations

import math


def usage_lock_threshold(use_counts: list[int], ratio: float = 0.667) -> int:
    if not use_counts:
        return 0
    if not 0 < ratio <= 1:
        raise ValueError("ratio must be in (0, 1]")
    ordered = sorted(use_counts)
    index = min(len(ordered) - 1, max(0, math.ceil(ratio * len(ordered)) - 1))
    return ordered[index]


def catalog_locked(use_count: int, threshold: int) -> bool:
    return threshold > 0 and use_count > threshold
